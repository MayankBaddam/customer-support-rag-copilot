from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from app.services.retrieval import MAX_SEARCH_QUERY_LENGTH


class SemanticSearchRequest(BaseModel):
    query: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=MAX_SEARCH_QUERY_LENGTH),
    ]
    top_k: int = Field(default=5, ge=1, le=10)


class SemanticSearchResultResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    chunk_id: UUID
    document_id: UUID
    document_title: str
    section_title: str | None
    page_number: int | None
    content: str
    similarity_score: float = Field(ge=-1, le=1)


class SemanticSearchResponse(BaseModel):
    request_id: UUID
    query: str
    results: list[SemanticSearchResultResponse]
    result_count: int
    retrieval_latency_ms: float
    embedding_model: str
    evidence_status: Literal["found", "no_evidence"]
