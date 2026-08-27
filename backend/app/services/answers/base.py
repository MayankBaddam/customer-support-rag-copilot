from dataclasses import dataclass
from typing import Protocol
from uuid import UUID


@dataclass(frozen=True, slots=True)
class GroundingContext:
    chunk_id: UUID
    document_id: UUID
    document_title: str
    original_filename: str
    section_title: str | None
    page_number: int | None
    content: str
    similarity_score: float


class AnswerProvider(Protocol):
    def generate_answer(self, query: str, contexts: list[GroundingContext]) -> str: ...


class AnswerProviderError(Exception):
    """Safe generation error that contains no prompts, context, or credentials."""


class AnswerTimeoutError(AnswerProviderError):
    pass


class AnswerQuotaError(AnswerProviderError):
    pass


class AnswerResponseError(AnswerProviderError):
    pass
