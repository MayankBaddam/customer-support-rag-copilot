from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from fastapi.testclient import TestClient

from app.api.dependencies import get_current_profile
from app.api.v1.copilot import get_answer_service
from app.core.config import Settings
from app.core.errors import APIError
from app.main import app
from app.models import Profile, ProfileRole
from app.repositories.semantic_search import SemanticSearchHit
from app.services.answer_generation import (
    INSUFFICIENT_CONTEXT_ANSWER,
    AnswerGenerationService,
    GroundedAnswerResult,
)
from app.services.answers import (
    AnswerProviderError,
    AnswerResponseError,
    AnswerTimeoutError,
    GROUNDING_SYSTEM_INSTRUCTION,
    GeminiAnswerProvider,
)
from app.services.retrieval import RetrievalResult


def answer_settings(**overrides) -> Settings:
    values = {
        "GEMINI_API_KEY": "test-key",
        "ANSWER_MODEL": "gemini-2.5-flash",
        "ANSWER_API_TIMEOUT_SECONDS": 5,
        "ANSWER_MAX_RETRIES": 2,
        "ANSWER_RETRY_BACKOFF_SECONDS": 0.01,
        "ANSWER_RETRY_MAX_BACKOFF_SECONDS": 0.02,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def make_hit(*, title="Account recovery", content="Recovery links remain valid for thirty minutes."):
    return SemanticSearchHit(
        chunk_id=uuid4(),
        document_id=uuid4(),
        document_title=title,
        original_filename="account-recovery.md",
        section_title="Recovery links",
        page_number=2,
        content=content,
        similarity_score=0.91,
    )


class StubRetrievalService:
    def __init__(self, results):
        self.results = tuple(results)
        self.calls = []

    def search(self, query, *, owner_id, top_k):
        self.calls.append({"query": query, "owner_id": owner_id, "top_k": top_k})
        return RetrievalResult(
            query=query.strip(),
            results=self.results,
            retrieval_latency_ms=1.0,
            embedding_model="gemini-embedding-001",
        )


class StubAnswerProvider:
    def __init__(self, effects):
        self.effects = list(effects)
        self.calls = []

    def generate_answer(self, query, contexts):
        self.calls.append({"query": query, "contexts": contexts})
        effect = self.effects.pop(0)
        if isinstance(effect, Exception):
            raise effect
        return effect


def test_grounded_answer_uses_only_retrieved_context_and_returns_citations():
    owner_id = uuid4()
    hit = make_hit()
    retrieval = StubRetrievalService([hit])
    provider = StubAnswerProvider(["Recovery links remain valid for thirty minutes."])
    service = AnswerGenerationService(retrieval, provider, answer_settings())

    result = service.answer("How long is recovery valid?", owner_id=owner_id, top_k=4)

    assert result.answer == "Recovery links remain valid for thirty minutes."
    assert result.citations == (hit,)
    assert result.retrieved_chunks == 1
    assert retrieval.calls == [{"query": "How long is recovery valid?", "owner_id": owner_id, "top_k": 4}]
    context = provider.calls[0]["contexts"][0]
    assert context.content == hit.content
    assert context.chunk_id == hit.chunk_id
    assert not hasattr(context, "embedding")


def test_insufficient_context_abstains_without_calling_answer_provider():
    provider = StubAnswerProvider(["unused"])
    result = AnswerGenerationService(
        StubRetrievalService([]), provider, answer_settings()
    ).answer("Unknown policy?", owner_id=uuid4(), top_k=5)

    assert result.answer == INSUFFICIENT_CONTEXT_ANSWER
    assert result.citations == ()
    assert result.retrieved_chunks == 0
    assert provider.calls == []


def test_timeout_retries_are_bounded_and_safe():
    provider = StubAnswerProvider([AnswerTimeoutError("detail")] * 3)
    delays = []
    service = AnswerGenerationService(
        StubRetrievalService([make_hit()]),
        provider,
        answer_settings(),
        sleeper=delays.append,
    )

    with pytest.raises(APIError) as caught:
        service.answer("private query", owner_id=uuid4(), top_k=5)

    assert caught.value.code == "ANSWER_TIMEOUT"
    assert caught.value.status_code == 504
    assert "private query" not in caught.value.message
    assert len(provider.calls) == 3
    assert delays == [0.01, 0.02]


def test_provider_error_is_sanitized_after_retry_limit():
    provider = StubAnswerProvider([AnswerProviderError("secret provider detail")])
    service = AnswerGenerationService(
        StubRetrievalService([make_hit()]),
        provider,
        answer_settings(ANSWER_MAX_RETRIES=0),
    )

    with pytest.raises(APIError) as caught:
        service.answer("private query", owner_id=uuid4(), top_k=5)

    assert caught.value.code == "ANSWER_GENERATION_FAILED"
    assert "secret" not in caught.value.message


def test_malformed_provider_response_is_not_retried():
    provider = StubAnswerProvider([AnswerResponseError("malformed")])
    service = AnswerGenerationService(StubRetrievalService([make_hit()]), provider, answer_settings())

    with pytest.raises(APIError) as caught:
        service.answer("question", owner_id=uuid4(), top_k=5)

    assert caught.value.code == "INVALID_ANSWER_RESPONSE"
    assert len(provider.calls) == 1


class MockModels:
    def __init__(self, effect):
        self.effect = effect
        self.calls = []

    def generate_content(self, **kwargs):
        self.calls.append(kwargs)
        if isinstance(self.effect, Exception):
            raise self.effect
        return self.effect


class MockClient:
    def __init__(self, effect):
        self.models = MockModels(effect)


def test_gemini_provider_uses_strict_instruction_and_context_only_prompt():
    hit = make_hit()
    context = SimpleNamespace(**{
        "chunk_id": hit.chunk_id,
        "document_id": hit.document_id,
        "document_title": hit.document_title,
        "original_filename": hit.original_filename,
        "section_title": hit.section_title,
        "page_number": hit.page_number,
        "content": hit.content,
        "similarity_score": hit.similarity_score,
    })
    client = MockClient(SimpleNamespace(text="Grounded response"))
    provider = GeminiAnswerProvider(client, answer_settings())

    answer = provider.generate_answer("How long?", [context])

    request = client.models.calls[0]
    assert answer == "Grounded response"
    assert request["model"] == "gemini-2.5-flash"
    assert request["config"].system_instruction == GROUNDING_SYSTEM_INSTRUCTION
    assert request["config"].temperature == 0.0
    assert "How long?" in request["contents"]
    assert hit.content in request["contents"]
    assert str(hit.chunk_id) in request["contents"]
    assert "embedding" not in request["contents"].lower()
    assert "test-key" not in request["contents"]


def test_gemini_provider_handles_timeout_and_malformed_response():
    context = SimpleNamespace(**vars(SimpleNamespace(
        chunk_id=uuid4(), document_id=uuid4(), document_title="Title",
        original_filename="source.txt", section_title=None, page_number=None,
        content="Evidence", similarity_score=0.8,
    )))
    with pytest.raises(AnswerTimeoutError):
        GeminiAnswerProvider(MockClient(httpx.ReadTimeout("detail")), answer_settings()).generate_answer("Question", [context])
    with pytest.raises(AnswerResponseError):
        GeminiAnswerProvider(MockClient(SimpleNamespace(text=None)), answer_settings()).generate_answer("Question", [context])


@pytest.fixture
def answer_api_client():
    profile = Profile(id=uuid4(), full_name="Answer Agent", role=ProfileRole.AGENT)
    hit = make_hit()

    class ApiAnswerService:
        def answer(self, query, *, owner_id, top_k):
            assert owner_id == profile.id
            assert top_k == 5
            assert query == "How long is recovery valid?"
            return GroundedAnswerResult(answer="Thirty minutes.", citations=(hit,))

    app.dependency_overrides[get_current_profile] = lambda: profile
    app.dependency_overrides[get_answer_service] = lambda: ApiAnswerService()
    with TestClient(app) as client:
        yield client, profile, hit
    app.dependency_overrides.clear()


def test_answer_api_is_grounded_and_owner_scoped(answer_api_client):
    client, _, hit = answer_api_client
    response = client.post(
        "/api/v1/copilot/answer",
        json={"query": "How long is recovery valid?", "top_k": 5},
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "answer": "Thirty minutes.",
        "citations": [{
            "chunk_id": str(hit.chunk_id),
            "document_title": hit.document_title,
            "original_filename": hit.original_filename,
            "section_title": hit.section_title,
            "page_number": hit.page_number,
            "similarity_score": hit.similarity_score,
        }],
        "retrieved_chunks": 1,
    }
    assert "embedding" not in response.text.lower()


def test_answer_api_requires_authentication():
    app.dependency_overrides.clear()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/copilot/answer",
            json={"query": "How long?", "top_k": 5},
        )

    assert response.status_code == 401
