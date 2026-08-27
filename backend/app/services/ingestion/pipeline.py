from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.models import Document, DocumentChunk, DocumentStatus
from app.services.ingestion.chunking import ChunkConfig, create_chunks
from app.services.ingestion.cleaning import normalize_document
from app.services.ingestion.extractors import extractor_for_file_type
from app.services.storage import SupabaseStorageAdapter


async def ingest_document(
    session: Session,
    document: Document,
    storage: SupabaseStorageAdapter,
    config: ChunkConfig | None = None,
) -> list[DocumentChunk]:
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
    document.status = DocumentStatus.COMPLETED
    document.chunk_count = len(chunks)
    document.processed_at = datetime.now(timezone.utc)
    session.add_all(chunks)
    session.commit()
    return chunks