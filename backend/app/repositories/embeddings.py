from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Document, DocumentChunk, DocumentStatus


class EmbeddingPersistenceError(ValueError):
    pass


class EmbeddingRepository:
    def __init__(self, session: Session, dimension: int = 768) -> None:
        self.session = session
        self.dimension = dimension

    def list_completed_chunks_without_embeddings(self, *, limit: int = 100) -> list[DocumentChunk]:
        statement = (
            select(DocumentChunk)
            .join(Document, Document.id == DocumentChunk.document_id)
            .where(Document.status == DocumentStatus.COMPLETED, DocumentChunk.embedding.is_(None))
            .order_by(DocumentChunk.document_id, DocumentChunk.chunk_index)
            .limit(limit)
        )
        return list(self.session.scalars(statement).all())

    def store_embeddings(
        self,
        items: list[tuple[UUID, list[float]]],
        *,
        overwrite: bool = False,
    ) -> int:
        chunk_ids = [chunk_id for chunk_id, _ in items]
        if len(set(chunk_ids)) != len(chunk_ids):
            raise EmbeddingPersistenceError("Duplicate chunk IDs are not allowed.")
        for _, vector in items:
            if len(vector) != self.dimension:
                raise EmbeddingPersistenceError(f"Embedding vectors must contain exactly {self.dimension} values.")
        if not items:
            return 0
        chunks = {
            chunk.id: chunk
            for chunk in self.session.scalars(select(DocumentChunk).where(DocumentChunk.id.in_(chunk_ids))).all()
        }
        missing = set(chunk_ids) - set(chunks)
        if missing:
            raise EmbeddingPersistenceError("One or more document chunks were not found.")
        stored = 0
        for chunk_id, vector in items:
            chunk = chunks[chunk_id]
            if chunk.embedding is not None and not overwrite:
                continue
            chunk.embedding = vector
            stored += 1
        self.session.flush()
        return stored
