from __future__ import annotations

from dataclasses import dataclass
from time import perf_counter
from typing import Callable
from uuid import UUID

from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import APIError
from app.repositories.semantic_search import SemanticSearchHit, SemanticSearchRepository
from app.services.embeddings import (
    EmbeddingDimensionError,
    EmbeddingProvider,
    EmbeddingProviderError,
    EmbeddingQuotaError,
    EmbeddingResponseError,
    EmbeddingTimeoutError,
)

MAX_SEARCH_QUERY_LENGTH = 1000


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    query: str
    results: tuple[SemanticSearchHit, ...]
    retrieval_latency_ms: float
    embedding_model: str

    @property
    def evidence_status(self) -> str:
        return "found" if self.results else "no_evidence"


class RetrievalService:
    def __init__(
        self,
        provider: EmbeddingProvider,
        repository: SemanticSearchRepository,
        settings: Settings | None = None,
        *,
        clock: Callable[[], float] = perf_counter,
    ) -> None:
        self.provider = provider
        self.repository = repository
        self.settings = settings or get_settings()
        self.clock = clock

    def embed_query(self, query: str) -> list[float]:
        normalized_query = query.strip()
        if not normalized_query:
            raise APIError("EMPTY_SEARCH_QUERY", "The search query must not be empty.", 422)
        if len(normalized_query) > MAX_SEARCH_QUERY_LENGTH:
            raise APIError("SEARCH_QUERY_TOO_LONG", "The search query is too long.", 422)
        try:
            vector = self.provider.embed_query(normalized_query)
        except EmbeddingTimeoutError as exc:
            raise APIError("EMBEDDING_TIMEOUT", "The query embedding provider timed out.", 504) from exc
        except EmbeddingQuotaError as exc:
            raise APIError("EMBEDDING_QUOTA_EXCEEDED", "The query embedding quota was exceeded.", 429) from exc
        except (EmbeddingDimensionError, EmbeddingResponseError) as exc:
            raise APIError("INVALID_QUERY_EMBEDDING", "The query embedding response was invalid.", 502) from exc
        except EmbeddingProviderError as exc:
            raise APIError("QUERY_EMBEDDING_FAILED", "The query could not be embedded.", 502) from exc
        if len(vector) != self.settings.embedding_dimension:
            raise APIError("INVALID_QUERY_EMBEDDING", "The query embedding response was invalid.", 502)
        return vector

    def search(self, query: str, *, owner_id: UUID, top_k: int) -> RetrievalResult:
        started_at = self.clock()
        normalized_query = query.strip()
        vector = self.embed_query(normalized_query)
        try:
            results = self.repository.search(vector, owner_id=owner_id, top_k=top_k)
        except Exception as exc:
            raise APIError("SEMANTIC_SEARCH_FAILED", "Semantic search is temporarily unavailable.", 503) from exc
        latency_ms = max(0.0, (self.clock() - started_at) * 1000)
        return RetrievalResult(
            query=normalized_query,
            results=tuple(results),
            retrieval_latency_ms=round(latency_ms, 3),
            embedding_model=self.settings.embedding_model,
        )


def get_retrieval_service(
    session: Session,
    provider: EmbeddingProvider,
) -> RetrievalService:
    settings = get_settings()
    return RetrievalService(
        provider,
        SemanticSearchRepository(session, settings.embedding_dimension),
        settings,
    )
