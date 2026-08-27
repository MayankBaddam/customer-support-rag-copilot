from typing import Annotated
from uuid import uuid4

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_profile
from app.database.session import get_db
from app.models import Profile
from app.schemas.semantic_search import (
    SemanticSearchRequest,
    SemanticSearchResponse,
    SemanticSearchResultResponse,
)
from app.services.embedding_generation import get_embedding_provider
from app.services.embeddings import EmbeddingProvider
from app.services.retrieval import RetrievalService, get_retrieval_service as build_retrieval_service

router = APIRouter(prefix="/copilot", tags=["copilot"])


def get_retrieval_service(
    session: Annotated[Session, Depends(get_db)],
    provider: Annotated[EmbeddingProvider, Depends(get_embedding_provider)],
) -> RetrievalService:
    return build_retrieval_service(session, provider)


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
