from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import Select, select
from sqlalchemy.orm import Session

from app.models import Document, DocumentChunk, DocumentStatus


@dataclass(frozen=True, slots=True)
class SemanticSearchHit:
    chunk_id: UUID
    document_id: UUID
    document_title: str
    original_filename: str
    section_title: str | None
    page_number: int | None
    content: str
    similarity_score: float


class SemanticSearchRepository:
    def __init__(self, session: Session, dimension: int = 768) -> None:
        self.session = session
        self.dimension = dimension

    def search(
        self,
        query_vector: list[float],
        *,
        owner_id: UUID,
        top_k: int,
    ) -> list[SemanticSearchHit]:
        if len(query_vector) != self.dimension:
            raise ValueError(f"Query vectors must contain exactly {self.dimension} values.")
        if not 1 <= top_k <= 10:
            raise ValueError("top_k must be between 1 and 10.")
        rows = self.session.execute(self.build_search_statement(query_vector, owner_id=owner_id, top_k=top_k))
        return [
            SemanticSearchHit(
                chunk_id=row.chunk_id,
                document_id=row.document_id,
                document_title=row.document_title,
                original_filename=row.original_filename,
                section_title=row.section_title,
                page_number=row.page_number,
                content=row.content,
                similarity_score=float(row.similarity_score),
            )
            for row in rows
        ]

    def build_search_statement(
        self,
        query_vector: list[float],
        *,
        owner_id: UUID,
        top_k: int,
    ) -> Select:
        cosine_distance = DocumentChunk.embedding.cosine_distance(query_vector)
        return (
            select(
                DocumentChunk.id.label("chunk_id"),
                Document.id.label("document_id"),
                Document.title.label("document_title"),
                Document.original_filename,
                DocumentChunk.section_title,
                DocumentChunk.page_number,
                DocumentChunk.content,
                (1 - cosine_distance).label("similarity_score"),
            )
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(
                Document.status == DocumentStatus.COMPLETED,
                Document.uploaded_by == owner_id,
                DocumentChunk.embedding.is_not(None),
            )
            .order_by(cosine_distance.asc())
            .limit(top_k)
        )
