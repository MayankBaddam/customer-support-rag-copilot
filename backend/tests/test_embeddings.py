import json
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Base, Document, DocumentChunk, DocumentFileType, DocumentStatus, Profile, ProfileRole
from app.repositories.embeddings import EmbeddingPersistenceError, EmbeddingRepository
from app.services.embeddings import (
    EmbeddingDimensionError,
    EmbeddingQuotaError,
    EmbeddingResponseError,
    EmbeddingTimeoutError,
    GeminiEmbeddingProvider,
)


def embedding_settings(**overrides) -> Settings:
    values = {
        "GEMINI_API_KEY": "test-api-key",
        "EMBEDDING_MODEL": "gemini-embedding-001",
        "EMBEDDING_DIMENSION": 768,
        "EMBEDDING_BATCH_SIZE": 2,
        "EMBEDDING_API_TIMEOUT_SECONDS": 4,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


def response_vectors(count: int, dimension: int = 768) -> dict:
    return {"embeddings": [{"values": [float(index)] * dimension} for index in range(count)]}


def test_embedding_configuration_defaults_and_secret_safety():
    settings = Settings(_env_file=None, GEMINI_API_KEY="secret-value")

    assert settings.embedding_model == "gemini-embedding-001"
    assert settings.embedding_dimension == 768
    assert settings.embedding_batch_size == 16
    assert settings.embedding_api_timeout_seconds == 30.0
    assert "gemini_api_key" not in settings.model_dump()
    assert "secret-value" not in str(settings.model_dump())


def test_provider_request_shape_and_query_task_type():
    captured = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append((request, json.loads(request.content)))
        return httpx.Response(200, json=response_vectors(1))

    provider = GeminiEmbeddingProvider(httpx.Client(transport=httpx.MockTransport(handler)), embedding_settings())
    vector = provider.embed_query("How do refunds work?")

    request, payload = captured[0]
    assert request.url.path.endswith("/models/gemini-embedding-001:batchEmbedContents")
    assert request.headers["x-goog-api-key"] == "test-api-key"
    assert payload["requests"][0] == {
        "model": "models/gemini-embedding-001",
        "content": {"parts": [{"text": "How do refunds work?"}]},
        "embedContentConfig": {"taskType": "RETRIEVAL_QUERY", "outputDimensionality": 768},
    }
    assert len(vector) == 768


def test_provider_batches_and_preserves_response_mapping():
    batch_sizes = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = json.loads(request.content)
        batch_sizes.append(len(payload["requests"]))
        start = sum(batch_sizes[:-1])
        return httpx.Response(200, json={"embeddings": [{"values": [float(start + index)] * 768} for index in range(batch_sizes[-1])]})

    provider = GeminiEmbeddingProvider(httpx.Client(transport=httpx.MockTransport(handler)), embedding_settings())
    vectors = provider.embed_texts(["one", "two", "three"])

    assert batch_sizes == [2, 1]
    assert [vector[0] for vector in vectors] == [0.0, 1.0, 2.0]


def test_provider_empty_input_makes_no_request():
    client = httpx.Client(transport=httpx.MockTransport(lambda _: pytest.fail("request was made")))
    assert GeminiEmbeddingProvider(client, embedding_settings()).embed_texts([]) == []


def test_provider_timeout_is_safe():
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("sensitive provider detail", request=request)

    provider = GeminiEmbeddingProvider(httpx.Client(transport=httpx.MockTransport(handler)), embedding_settings())
    with pytest.raises(EmbeddingTimeoutError, match="timed out") as caught:
        provider.embed_texts(["private document content"])
    assert "private document" not in str(caught.value)


def test_provider_quota_error_is_safe():
    provider = GeminiEmbeddingProvider(
        httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(429, json={"error": "provider detail"}))),
        embedding_settings(),
    )
    with pytest.raises(EmbeddingQuotaError, match="quota"):
        provider.embed_texts(["content"])


@pytest.mark.parametrize("payload", [{}, {"embeddings": []}, {"embeddings": [{"wrong": []}]}])
def test_provider_rejects_malformed_responses(payload):
    provider = GeminiEmbeddingProvider(
        httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=payload))),
        embedding_settings(),
    )
    with pytest.raises(EmbeddingResponseError):
        provider.embed_texts(["content"])


def test_provider_rejects_wrong_vector_dimension():
    provider = GeminiEmbeddingProvider(
        httpx.Client(transport=httpx.MockTransport(lambda _: httpx.Response(200, json=response_vectors(1, 767)))),
        embedding_settings(),
    )
    with pytest.raises(EmbeddingDimensionError, match="wrong dimension"):
        provider.embed_texts(["content"])


@pytest.fixture
def embedding_session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    engine.dispose()


def make_chunk(session: Session, *, status: DocumentStatus = DocumentStatus.COMPLETED, embedded: bool = False) -> DocumentChunk:
    profile = Profile(id=uuid4(), full_name="Embedding Agent", role=ProfileRole.AGENT)
    document = Document(
        title="Embedding source", original_filename=f"{uuid4()}.txt", storage_bucket="private",
        storage_path=f"user/{uuid4()}/source.txt", file_type=DocumentFileType.TEXT, mime_type="text/plain",
        file_size_bytes=20, checksum_sha256=str(uuid4()), status=status, uploaded_by=profile.id,
    )
    chunk = DocumentChunk(document=document, chunk_index=0, content="Chunk content", token_count=2, embedding=[0.0] * 768 if embedded else None)
    session.add_all([profile, document, chunk]); session.commit()
    return chunk


def test_repository_finds_only_completed_chunks_without_embeddings(embedding_session):
    expected = make_chunk(embedding_session)
    make_chunk(embedding_session, status=DocumentStatus.PENDING)
    make_chunk(embedding_session, embedded=True)

    assert EmbeddingRepository(embedding_session).list_completed_chunks_without_embeddings() == [expected]


def test_successful_embedding_persistence_does_not_overwrite_by_default(embedding_session):
    chunk = make_chunk(embedding_session)
    repository = EmbeddingRepository(embedding_session)
    first = [0.25] * 768
    second = [0.75] * 768

    assert repository.store_embeddings([(chunk.id, first)]) == 1
    assert repository.store_embeddings([(chunk.id, second)]) == 0
    embedding_session.refresh(chunk)
    assert list(chunk.embedding) == first
    assert repository.store_embeddings([(chunk.id, second)], overwrite=True) == 1


def test_embedding_persistence_rejects_missing_duplicate_and_wrong_dimension(embedding_session):
    chunk = make_chunk(embedding_session)
    repository = EmbeddingRepository(embedding_session)

    with pytest.raises(EmbeddingPersistenceError, match="not found"):
        repository.store_embeddings([(uuid4(), [0.0] * 768)])
    with pytest.raises(EmbeddingPersistenceError, match="Duplicate"):
        repository.store_embeddings([(chunk.id, [0.0] * 768), (chunk.id, [1.0] * 768)])
    with pytest.raises(EmbeddingPersistenceError, match="768"):
        repository.store_embeddings([(chunk.id, [0.0] * 767)])
