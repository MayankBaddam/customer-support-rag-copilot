from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_profile
from app.database.session import get_db
from app.models import Profile
from app.schemas.semantic_search import (
    GroundedAnswerCitation,
    GroundedAnswerResponse,
    SemanticSearchRequest,
    SemanticSearchResponse,
    SemanticSearchResultResponse,
)
from app.core.errors import APIError
from app.services.answer_generation import (
    AnswerGenerationService,
    get_answer_provider as build_answer_provider,
)
from app.services.answers import AnswerProvider, AnswerProviderError
from app.services.embedding_generation import get_embedding_provider
from app.services.embeddings import EmbeddingProvider
from app.services.retrieval import RetrievalService, get_retrieval_service as build_retrieval_service

router = APIRouter(prefix="/copilot", tags=["copilot"])


def get_retrieval_service(
    session: Annotated[Session, Depends(get_db)],
    provider: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
) -> RetrievalService:
    return build_retrieval_service(session, provider)


def get_answer_provider() -> AnswerProvider:
    try:
        return build_answer_provider()
    except AnswerProviderError as exc:
        raise APIError("ANSWER_PROVIDER_NOT_CONFIGURED", "The answer provider is not configured.", 503) from exc


def get_answer_service(
    retrieval_service: Annotated[RetrievalService, Depends(get_retrieval_service)],
    provider: Annotated[AnswerProvider, Depends(get_answer_provider)],
) -> AnswerGenerationService:
    return AnswerGenerationService(retrieval_service, provider)


@router.post("/search", response_model=SemanticSearchResponse)
def semantic_search(
    request: SemanticSearchRequest,
    profile: Annotated[Profile, Depends(get_current_profile)],
    service: Annotated[RetrievalService, Depends(get_retrieval_service)],
) -> SemanticSearchResponse:
    retrieval = service.search(request.query, owner_id=profile.id, top_k=request.top_k)
    results = [SemanticSearchResultResponse.model_validate(result) for result in retrieval.results]
    return SemanticSearchResponse(
        request_id=uuid4(),
        query=retrieval.query,
        results=results,
        result_count=len(results),
        retrieval_latency_ms=retrieval.retrieval_latency_ms,
        embedding_model=retrieval.embedding_model,
        evidence_status=retrieval.evidence_status,
    )


@router.post("/answer", response_model=GroundedAnswerResponse)
def grounded_answer(
    request: SemanticSearchRequest,
    profile: Annotated[Profile, Depends(get_current_profile)],
    service: Annotated[AnswerGenerationService, Depends(get_answer_service)],
) -> GroundedAnswerResponse:
    result = service.answer(request.query, owner_id=profile.id, top_k=request.top_k)
    citations = [
        GroundedAnswerCitation(
            chunk_id=hit.chunk_id,
            document_title=hit.document_title,
            original_filename=hit.original_filename,
            section_title=hit.section_title,
            page_number=hit.page_number,
            similarity_score=hit.similarity_score,
        )
        for hit in result.citations
    ]
    return GroundedAnswerResponse(
        answer=result.answer,
        citations=citations,
        retrieved_chunks=result.retrieved_chunks,
    )
