from __future__ import annotations

from dataclasses import asdict, dataclass
from time import sleep
from typing import Callable
from uuid import UUID

from app.core.config import Settings, get_settings
from app.core.errors import APIError
from app.repositories.semantic_search import SemanticSearchHit
from app.services.answers import (
    AnswerProvider,
    AnswerProviderError,
    AnswerQuotaError,
    AnswerResponseError,
    AnswerTimeoutError,
    GeminiAnswerProvider,
    GroundingContext,
)
from app.services.retrieval import RetrievalService

INSUFFICIENT_CONTEXT_ANSWER = "The knowledge base does not contain enough information to answer this question."


@dataclass(frozen=True, slots=True)
class GroundedAnswerResult:
    answer: str
    citations: tuple[SemanticSearchHit, ...]

    @property
    def retrieved_chunks(self) -> int:
        return len(self.citations)


class AnswerGenerationService:
    def __init__(
        self,
        retrieval_service: RetrievalService,
        provider: AnswerProvider,
        settings: Settings | None = None,
        *,
        sleeper: Callable[[float], None] = sleep,
    ) -> None:
        self.retrieval_service = retrieval_service
        self.provider = provider
        self.settings = settings or get_settings()
        self.sleeper = sleeper

    def answer(self, query: str, *, owner_id: UUID, top_k: int) -> GroundedAnswerResult:
        retrieval = self.retrieval_service.search(query, owner_id=owner_id, top_k=top_k)
        if not retrieval.results:
            return GroundedAnswerResult(answer=INSUFFICIENT_CONTEXT_ANSWER, citations=())
        contexts = [GroundingContext(**asdict(hit)) for hit in retrieval.results]
        answer = self._generate_with_retry(retrieval.query, contexts)
        return GroundedAnswerResult(answer=answer, citations=retrieval.results)

    def _generate_with_retry(self, query: str, contexts: list[GroundingContext]) -> str:
        attempt = 0
        while True:
            try:
                return self.provider.generate_answer(query, contexts)
            except AnswerResponseError as exc:
                raise APIError("INVALID_ANSWER_RESPONSE", "The answer provider returned an invalid response.", 502) from exc
            except AnswerTimeoutError as exc:
                if attempt >= self.settings.answer_max_retries:
                    raise APIError("ANSWER_TIMEOUT", "The answer provider timed out.", 504) from exc
            except AnswerQuotaError as exc:
                if attempt >= self.settings.answer_max_retries:
                    raise APIError("ANSWER_QUOTA_EXCEEDED", "The answer provider quota was exceeded.", 429) from exc
            except AnswerProviderError as exc:
                if attempt >= self.settings.answer_max_retries:
                    raise APIError("ANSWER_GENERATION_FAILED", "The grounded answer could not be generated.", 502) from exc
            delay = min(
                self.settings.answer_retry_backoff_seconds * (2 ** attempt),
                self.settings.answer_retry_max_backoff_seconds,
            )
            if delay:
                self.sleeper(delay)
            attempt += 1


def get_answer_provider() -> AnswerProvider:
    return GeminiAnswerProvider()
