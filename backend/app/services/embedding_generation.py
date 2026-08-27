from __future__ import annotations

from dataclasses import dataclass
from time import sleep
from typing import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.repositories.embeddings import EmbeddingRepository
from app.services.embeddings import (
    EmbeddingDimensionError,
    EmbeddingProvider,
    EmbeddingProviderError,
    EmbeddingResponseError,
    GeminiEmbeddingProvider,
)


@dataclass(frozen=True, slots=True)
class EmbeddingFailure:
    exception_type: str
    message: str
    http_status: int | None
    retry_count: int
    stage: str


@dataclass(frozen=True, slots=True)
class EmbeddingRunResult:
    processed: int = 0
    skipped: int = 0
    failed: int = 0
    failures: tuple[EmbeddingFailure, ...] = ()

    @property
    def status(self) -> str:
        return "completed" if self.failed == 0 else "partial_failure"


def get_embedding_provider() -> EmbeddingProvider:
    return GeminiEmbeddingProvider()


class EmbeddingGenerationService:
    def __init__(
        self,
        session: Session,
        provider: EmbeddingProvider,
        settings: Settings | None = None,
        *,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        self.session = session
        self.provider = provider
        self.settings = settings or get_settings()
        self.repository = EmbeddingRepository(session, self.settings.embedding_dimension)
        self.sleeper = sleeper

    def run(
        self,
        *,
        document_id: UUID | None = None,
        batch_size: int | None = None,
        force: bool = False,
        limit: int | None = None,
        dry_run: bool = False,
    ) -> EmbeddingRunResult:
        effective_batch_size = batch_size or self.settings.embedding_batch_size
        if effective_batch_size <= 0:
            raise ValueError("batch_size must be greater than zero")
        if limit is not None and limit <= 0:
            raise ValueError("limit must be greater than zero")
        chunks = self.repository.list_completed_chunks_without_embeddings(
            document_id=document_id,
            limit=limit,
            include_embedded=force,
        )
        existing = 0 if force else self.repository.count_completed_chunks_with_embeddings(document_id=document_id)
        if dry_run:
            return EmbeddingRunResult(skipped=existing + len(chunks))
        processed = 0
        skipped = existing
        failed = 0
        failures: list[EmbeddingFailure] = []
        for start in range(0, len(chunks), effective_batch_size):
            batch = chunks[start : start + effective_batch_size]
            try:
                vectors = self._embed_with_retry([chunk.content for chunk in batch])
                self._validate_vectors(vectors, len(batch))
            except EmbeddingProviderError as exc:
                failed += len(batch)
                failures.append(
                    EmbeddingFailure(
                        exception_type=exc.exception_type,
                        message=str(exc),
                        http_status=exc.http_status,
                        retry_count=exc.retry_count,
                        stage=exc.stage,
                    )
                )
                continue
            try:
                stored = self.repository.store_embeddings(
                    [(chunk.id, vector) for chunk, vector in zip(batch, vectors, strict=True)],
                    overwrite=force,
                )
                self.session.commit()
                processed += stored
                skipped += len(batch) - stored
            except Exception as exc:
                self.session.rollback()
                failed += len(batch)
                failures.append(
                    EmbeddingFailure(
                        exception_type=type(exc).__name__,
                        message="The embedding database transaction failed.",
                        http_status=None,
                        retry_count=0,
                        stage="after_provider_request",
                    )
                )
        return EmbeddingRunResult(
            processed=processed,
            skipped=skipped,
            failed=failed,
            failures=tuple(failures),
        )

    def _embed_with_retry(self, texts: list[str]) -> list[list[float]]:
        attempt = 0
        while True:
            try:
                return self.provider.embed_texts(texts)
            except EmbeddingResponseError:
                raise
            except EmbeddingProviderError as exc:
                if attempt >= self.settings.embedding_max_retries:
                    exc.retry_count = attempt
                    raise
                delay = min(
                    self.settings.embedding_retry_backoff_seconds * (2 ** attempt),
                    self.settings.embedding_retry_max_backoff_seconds,
                )
                if delay:
                    self.sleeper(delay)
                attempt += 1

    def _validate_vectors(self, vectors: list[list[float]], expected_count: int) -> None:
        if len(vectors) != expected_count:
            raise EmbeddingResponseError("The embedding provider returned an unexpected number of vectors.")
        if any(len(vector) != self.settings.embedding_dimension for vector in vectors):
            raise EmbeddingDimensionError("The embedding provider returned a vector with the wrong dimension.")
