from uuid import UUID, uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.models import Base, Document, DocumentChunk, DocumentFileType, DocumentStatus, Profile, ProfileRole
from app.services.embedding_generation import EmbeddingGenerationService, EmbeddingRunResult
from app.services.embeddings import EmbeddingQuotaError, EmbeddingTimeoutError


def settings(**overrides) -> Settings:
    values = {
        "GEMINI_API_KEY": "test-key",
        "EMBEDDING_DIMENSION": 768,
        "EMBEDDING_BATCH_SIZE": 2,
        "EMBEDDING_MAX_RETRIES": 2,
        "EMBEDDING_RETRY_BACKOFF_SECONDS": 0.01,
        "EMBEDDING_RETRY_MAX_BACKOFF_SECONDS": 0.02,
    }
    values.update(overrides)
    return Settings(_env_file=None, **values)


class StubProvider:
    def __init__(self, effects=None):
        self.effects = list(effects or [])
        self.calls: list[list[str]] = []

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        self.calls.append(list(texts))
        if self.effects:
            effect = self.effects.pop(0)
            if isinstance(effect, Exception):
                raise effect
            return effect
        return [[float(index)] * 768 for index, _ in enumerate(texts)]

    def embed_query(self, text: str) -> list[float]:
        raise AssertionError("query embedding is outside this task")


@pytest.fixture
def session():
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine)
    with Session(engine) as database_session:
        yield database_session
    engine.dispose()


def make_document(
    session: Session,
    *,
    count: int = 1,
    status: DocumentStatus = DocumentStatus.COMPLETED,
    embedded: set[int] | None = None,
) -> tuple[Document, list[DocumentChunk]]:
    profile = Profile(id=uuid4(), full_name="Backfill Agent", role=ProfileRole.AGENT)
    document = Document(
        title="Backfill source",
        original_filename=f"{uuid4()}.txt",
        storage_bucket="private",
        storage_path=f"user/{uuid4()}/source.txt",
        file_type=DocumentFileType.TEXT,
        mime_type="text/plain",
        file_size_bytes=20,
        checksum_sha256=str(uuid4()),
        status=status,
        uploaded_by=profile.id,
    )
    chunks = [
        DocumentChunk(
            document=document,
            chunk_index=index,
            content=f"chunk-{index}",
            token_count=1,
            embedding=[9.0] * 768 if index in (embedded or set()) else None,
        )
        for index in range(count)
    ]
    session.add_all([profile, document, *chunks])
    session.commit()
    return document, chunks


def test_selects_only_completed_documents_and_null_embeddings(session):
    _, eligible = make_document(session, count=2, embedded={1})
    make_document(session, status=DocumentStatus.PENDING)
    make_document(session, status=DocumentStatus.ARCHIVED)
    provider = StubProvider()

    result = EmbeddingGenerationService(session, provider, settings()).run()

    assert result.processed == 1
    assert result.skipped == 1
    assert result.failed == 0
    assert provider.calls == [[eligible[0].content]]


def test_batches_map_vectors_to_the_correct_chunks(session):
    _, chunks = make_document(session, count=3)
    provider = StubProvider(
        [
            [[1.0] * 768, [2.0] * 768],
            [[3.0] * 768],
        ]
    )

    result = EmbeddingGenerationService(session, provider, settings()).run(batch_size=2)

    assert result.processed == 3
    assert [len(call) for call in provider.calls] == [2, 1]
    for chunk, expected in zip(chunks, (1.0, 2.0, 3.0), strict=True):
        session.refresh(chunk)
        assert chunk.embedding[0] == expected


def test_force_replaces_existing_embeddings(session):
    document, chunks = make_document(session, embedded={0})
    provider = StubProvider([[[4.0] * 768]])

    result = EmbeddingGenerationService(session, provider, settings()).run(document_id=document.id, force=True)

    session.refresh(chunks[0])
    assert result.processed == 1
    assert result.skipped == 0
    assert chunks[0].embedding[0] == 4.0


def test_empty_selection_and_dry_run_make_no_provider_calls(session):
    document, _ = make_document(session, status=DocumentStatus.PENDING)
    provider = StubProvider()
    service = EmbeddingGenerationService(session, provider, settings())

    assert service.run(document_id=document.id).processed == 0
    completed, _ = make_document(session, count=2)
    dry_run = service.run(document_id=completed.id, dry_run=True)

    assert dry_run.processed == 0
    assert dry_run.skipped == 2
    assert provider.calls == []


@pytest.mark.parametrize(
    "vectors",
    [
        [[1.0] * 768],
        [[1.0] * 767, [2.0] * 768],
    ],
)
def test_invalid_batch_response_is_not_persisted(session, vectors):
    _, chunks = make_document(session, count=2)
    provider = StubProvider([vectors])

    result = EmbeddingGenerationService(session, provider, settings()).run(batch_size=2)

    assert result.failed == 2
    assert len(provider.calls) == 1
    session.expire_all()
    assert all(session.get(DocumentChunk, chunk.id).embedding is None for chunk in chunks)


@pytest.mark.parametrize("error", [EmbeddingTimeoutError("timeout"), EmbeddingQuotaError("quota")])
def test_transient_provider_errors_retry_then_succeed(session, error):
    _, chunks = make_document(session)
    provider = StubProvider([error, error, [[5.0] * 768]])
    delays = []

    result = EmbeddingGenerationService(session, provider, settings(), sleeper=delays.append).run()

    assert result.processed == 1
    assert len(provider.calls) == 3
    assert delays == [0.01, 0.02]
    session.refresh(chunks[0])
    assert chunks[0].embedding[0] == 5.0


def test_retry_limit_reports_failed_batch(session):
    make_document(session)
    provider = StubProvider([EmbeddingQuotaError("quota")] * 3)

    result = EmbeddingGenerationService(session, provider, settings(), sleeper=lambda _: None).run()

    assert result.failed == 1
    assert len(provider.calls) == 3
    assert result.status == "partial_failure"


def test_partial_failure_preserves_earlier_committed_batch(session):
    _, chunks = make_document(session, count=2)
    provider = StubProvider([[[6.0] * 768], []])

    result = EmbeddingGenerationService(session, provider, settings()).run(batch_size=1)

    assert (result.processed, result.failed) == (1, 1)
    session.expire_all()
    assert session.get(DocumentChunk, chunks[0].id).embedding[0] == 6.0
    assert session.get(DocumentChunk, chunks[1].id).embedding is None


def test_database_failure_rolls_back_the_batch(session, monkeypatch):
    _, chunks = make_document(session)
    service = EmbeddingGenerationService(session, StubProvider(), settings())

    def fail_after_write(items, *, overwrite=False):
        chunks[0].embedding = items[0][1]
        session.flush()
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(service.repository, "store_embeddings", fail_after_write)
    result = service.run()

    assert result.failed == 1
    session.expire_all()
    assert session.get(DocumentChunk, chunks[0].id).embedding is None


def test_rerun_is_idempotent(session):
    document, _ = make_document(session)
    provider = StubProvider()
    service = EmbeddingGenerationService(session, provider, settings())

    first = service.run(document_id=document.id)
    second = service.run(document_id=document.id)

    assert first.processed == 1
    assert second.processed == 0
    assert second.skipped == 1
    assert len(provider.calls) == 1


def test_limit_restricts_selected_chunks(session):
    make_document(session, count=3)
    provider = StubProvider()

    result = EmbeddingGenerationService(session, provider, settings()).run(limit=2)

    assert result.processed == 2
    assert sum(len(call) for call in provider.calls) == 2


def test_cli_forwards_all_options_and_returns_nonzero_for_failures(monkeypatch, capsys):
    import app.embedding_backfill as cli

    document_id = uuid4()
    captured = {}

    class FakeSession:
        def __init__(self, _engine):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    class FakeService:
        def __init__(self, *_args):
            pass

        def run(self, **kwargs):
            captured.update(kwargs)
            return EmbeddingRunResult(processed=2, skipped=3, failed=1)

    monkeypatch.setattr(cli, "Session", FakeSession)
    monkeypatch.setattr(cli, "get_database_engine", lambda: object())
    monkeypatch.setattr(cli, "GeminiEmbeddingProvider", lambda **_kwargs: object())
    monkeypatch.setattr(cli, "EmbeddingGenerationService", FakeService)

    exit_code = cli.main(
        ["--dry-run", "--document-id", str(document_id), "--batch-size", "4", "--force", "--limit", "9"]
    )

    assert exit_code == 1
    assert captured == {
        "document_id": UUID(str(document_id)),
        "batch_size": 4,
        "force": True,
        "limit": 9,
        "dry_run": True,
    }
    assert '"processed": 2' in capsys.readouterr().out
