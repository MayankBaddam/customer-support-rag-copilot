from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.models import Document, DocumentChunk, DocumentStatus
from app.services.ingestion.chunking import ChunkConfig, create_chunks
from app.services.ingestion.cleaning import normalize_document
from app.services.ingestion.extractors import extractor_for_file_type
from app.services.storage import SupabaseStorageAdapter


def _safe_failure_message(error: Exception) -> str:
    if hasattr(error, "code") and str(getattr(error, "code", "")).startswith("STORAGE_"):
        return "Document storage operation failed."
    if isinstance(error, ValueError):
        return str(error)[:240] or "Document processing failed."
    return "Document processing failed."


async def ingest_document(
    session: Session,
    document: Document,
    storage: SupabaseStorageAdapter,
    config: ChunkConfig | None = None,
) -> list[DocumentChunk]:
    try:
        content = await storage.download_object(bucket=document.storage_bucket, path=document.storage_path)
        extracted = extractor_for_file_type(document.file_type).extract(
            content, document_id=document.id, source_filename=document.original_filename
        )
        normalized = normalize_document(extracted)
        if not normalized.blocks:
            raise ValueError("The document contains no extractable text")

        drafts = create_chunks(normalized, config)
        if not drafts:
            raise ValueError("The document contains no extractable text")
        chunks = [
            DocumentChunk(
                document_id=document.id,
                chunk_index=draft.chunk_index,
                content=draft.content,
                section_title=draft.section_title,
                page_number=draft.page_number,
                token_count=draft.token_count,
                chunk_metadata=draft.metadata,
            )
            for draft in drafts
        ]
        session.execute(delete(DocumentChunk).where(DocumentChunk.document_id == document.id))
        session.add_all(chunks)
        document.status = DocumentStatus.COMPLETED
        document.chunk_count = len(chunks)
        document.processed_at = datetime.now(timezone.utc)
        document.error_message = None
        session.commit()
        return chunks
    except Exception as exc:
        session.rollback()
        document.status = DocumentStatus.FAILED
        document.error_message = _safe_failure_message(exc)
        session.commit()
        raise