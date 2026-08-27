from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.dialects import postgresql

from app.api.dependencies import get_current_profile
from app.api.v1.copilot import get_retrieval_service
from app.core.config import Settings
from app.core.errors import APIError
from app.main import app
from app.models import DocumentStatus, Profile, ProfileRole
from app.repositories.semantic_search import SemanticSearchHit, SemanticSearchRepository
from app.services.embeddings import EmbeddingQuotaError, EmbeddingTimeoutError
from app.services.retrieval import MAX_SEARCH_QUERY_LENGTH, RetrievalResult, RetrievalService


def search_settings() -> Settings:
    return Settings(
        _env_file=None,
        GEMINI_API_KEY="test-key",
        EMBEDDING_MODEL="gemini-embedding-001",
        EMBEDDING_DIMENSION=768,
    )


class StubProvider:
    def __init__(self, effect=None):
        self.effect = effect if effect is not None else [0.1] * 768
        self.queries = []

    def embed_query(self, text):
        self.queries.append(text)
        if isinstance(self.effect, Exception):
            raise self.effect
        return self.effect

    def embed_texts(self, _texts):
        raise AssertionError("document embedding is outside this test")


class StubRepository:
    def __init__(self, results=None, error=None):
        self.results = list(results or [])
        self.error = error
        self.calls = []

    def search(self, vector, *, owner_id, top_k):
        self.calls.append({"vector": vector, "owner_id": owner_id, "top_k": top_k})
        if self.error:
            raise self.error
        return self.results


def make_hit(score=0.85):
    return SemanticSearchHit(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_title="Account recovery",
        section_title="Recovery links",
        page_number=2,
        content="Recovery links remain valid for a limited time.",
        similarity_score=score,
    )


def test_successful_query_embedding_and_retrieval_latency():
    owner_id = uuid4()
    provider = StubProvider()
    repository = StubRepository([make_hit()])
    ticks = iter([10.0, 10.0125])
    service = RetrievalService(provider, repository, search_settings(), clock=lambda: next(ticks))

    result = service.search("  How long is recovery valid?  ", owner_id=owner_id, top_k=5)

    assert provider.queries == ["How long is recovery valid?"]
    assert repository.calls == [{"vector": [0.1] * 768, "owner_id": owner_id, "top_k": 5}]
    assert result.query == "How long is recovery valid?"
    assert result.retrieval_latency_ms == 12.5
    assert result.embedding_model == "gemini-embedding-001"
    assert result.evidence_status == "found"


@pytest.mark.parametrize("query", ["", "   "])
def test_empty_query_is_rejected_before_provider_call(query):
    provider = StubProvider()
    service = RetrievalService(provider, StubRepository(), search_settings())

    with pytest.raises(APIError) as caught:
        service.embed_query(query)

    assert caught.value.code == "EMPTY_SEARCH_QUERY"
    assert provider.queries == []


def test_query_length_limit_is_enforced():
    provider = StubProvider()
    service = RetrievalService(provider, StubRepository(), search_settings())

    with pytest.raises(APIError) as caught:
        service.embed_query("x" * (MAX_SEARCH_QUERY_LENGTH + 1))

    assert caught.value.code == "SEARCH_QUERY_TOO_LONG"
    assert provider.queries == []


def test_wrong_query_vector_dimension_is_rejected():
    service = RetrievalService(StubProvider([0.1] * 767), StubRepository(), search_settings())

    with pytest.raises(APIError) as caught:
        service.search("valid query", owner_id=uuid4(), top_k=5)

    assert caught.value.code == "INVALID_QUERY_EMBEDDING"


@pytest.mark.parametrize(
    ("error", "expected_code", "status_code"),
    [
        (EmbeddingTimeoutError("timeout"), "EMBEDDING_TIMEOUT", 504),
        (EmbeddingQuotaError("quota"), "EMBEDDING_QUOTA_EXCEEDED", 429),
    ],
)
def test_provider_failures_are_safe(error, expected_code, status_code):
    service = RetrievalService(StubProvider(error), StubRepository(), search_settings())

    with pytest.raises(APIError) as caught:
        service.search("private query", owner_id=uuid4(), top_k=5)

    assert caught.value.code == expected_code
    assert caught.value.status_code == status_code
    assert "private query" not in caught.value.message


def test_database_error_is_safe():
    service = RetrievalService(
        StubProvider(),
        StubRepository(error=RuntimeError("database URL and internal detail")),
        search_settings(),
    )

    with pytest.raises(APIError) as caught:
        service.search("private query", owner_id=uuid4(), top_k=5)

    assert caught.value.code == "SEMANTIC_SEARCH_FAILED"
    assert caught.value.status_code == 503
    assert "database" not in caught.value.message.lower()


def test_no_results_returns_no_evidence():
    result = RetrievalService(StubProvider(), StubRepository(), search_settings()).search(
        "valid query", owner_id=uuid4(), top_k=3
    )

    assert result.results == ()
    assert result.evidence_status == "no_evidence"


class FakeSearchSession:
    def __init__(self, rows=()):
        self.rows = rows
        self.statement = None

    def execute(self, statement):
        self.statement = statement
        return self.rows


def test_successful_cosine_search_maps_fields_without_embedding():
    row = SimpleNamespace(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_title="Retention policy",
        section_title=None,
        page_number=None,
        content="Data is retained for the configured period.",
        similarity_score=0.72,
    )
    session = FakeSearchSession([row])

    results = SemanticSearchRepository(session).search([0.1] * 768, owner_id=uuid4(), top_k=1)

    assert len(results) == 1
    assert results[0].content == row.content
    assert results[0].similarity_score == 0.72
    assert not hasattr(results[0], "embedding")
    compiled = str(session.statement.compile(dialect=postgresql.dialect()))
    assert "<=>" in compiled
    assert "ORDER BY" in compiled


def test_repository_filters_completed_embedded_chunks_by_owner():
    owner_id = uuid4()
    repository = SemanticSearchRepository(FakeSearchSession())
    statement = repository.build_search_statement([0.1] * 768, owner_id=owner_id, top_k=5)
    compiled = statement.compile(dialect=postgresql.dialect())
    sql = str(compiled)

    assert "documents.status" in sql
    assert "documents.uploaded_by" in sql
    assert "document_chunks.embedding IS NOT NULL" in sql
    assert DocumentStatus.COMPLETED in compiled.params.values()
    assert owner_id in compiled.params.values()
    for excluded in (DocumentStatus.ARCHIVED, DocumentStatus.FAILED, DocumentStatus.PENDING):
        assert excluded not in compiled.params.values()


@pytest.mark.parametrize("top_k", [0, 11])
def test_repository_rejects_top_k_out_of_bounds(top_k):
    with pytest.raises(ValueError, match="top_k"):
        SemanticSearchRepository(FakeSearchSession()).search([0.1] * 768, owner_id=uuid4(), top_k=top_k)


@pytest.fixture
def search_api_client():
    profile = Profile(id=uuid4(), full_name="Search Agent", role=ProfileRole.AGENT)
    hit = make_hit()

    class ApiService:
        def search(self, query, *, owner_id, top_k):
            assert owner_id == profile.id
            assert top_k == 5
            return RetrievalResult(
                query=query,
                results=(hit,),
                retrieval_latency_ms=4.25,
                embedding_model="gemini-embedding-001",
            )

    app.dependency_overrides[get_current_profile] = lambda: profile
    app.dependency_overrides[get_retrieval_service] = lambda: ApiService()
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


def test_search_api_returns_typed_response_without_vectors(search_api_client):
    response = search_api_client.post(
        "/api/v1/copilot/search",
        json={"query": "How long is a recovery link valid?", "top_k": 5},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["query"] == "How long is a recovery link valid?"
    assert payload["result_count"] == 1
    assert payload["retrieval_latency_ms"] == 4.25
    assert payload["embedding_model"] == "gemini-embedding-001"
    assert payload["evidence_status"] == "found"
    assert payload["request_id"]
    assert "embedding" not in payload["results"][0]
    assert "vector" not in response.text.lower()


@pytest.mark.parametrize(
    "body",
    [
        {"query": " ", "top_k": 5},
        {"query": "x" * (MAX_SEARCH_QUERY_LENGTH + 1), "top_k": 5},
        {"query": "valid", "top_k": 0},
        {"query": "valid", "top_k": 11},
    ],
)
def test_search_api_validates_query_and_top_k(search_api_client, body):
    assert search_api_client.post("/api/v1/copilot/search", json=body).status_code == 422


def test_search_api_requires_authentication():
    app.dependency_overrides.clear()
    with TestClient(app) as client:
        response = client.post("/api/v1/copilot/search", json={"query": "valid", "top_k": 5})

    assert response.status_code == 401
