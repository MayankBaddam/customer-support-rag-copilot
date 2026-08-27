from __future__ import annotations

import hashlib
import os
import re
from pathlib import PurePosixPath
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, Query, Response, UploadFile, status
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_profile
from app.database.session import get_db
from app.core.config import get_settings
from app.core.errors import APIError
from app.models import Document, DocumentChunk, DocumentFileType, DocumentStatus, Profile
from app.schemas.documents import (
    DocumentChunkListResponse,
    DocumentChunkResponse,
    DocumentListResponse,
    DocumentResponse,
)
from app.services.ingestion import ingest_document
from app.services.storage import SupabaseStorageAdapter, get_storage_adapter

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_TYPES = {
    ".pdf": (DocumentFileType.PDF, "application/pdf"),
    ".md": (DocumentFileType.MARKDOWN, "text/markdown"),
    ".markdown": (DocumentFileType.MARKDOWN, "text/markdown"),
    ".txt": (DocumentFileType.TEXT, "text/plain"),
}
ALLOWED_MIME_TYPES = {"application/pdf", "text/plain", "text/markdown", "text/x-markdown"}


def _safe_filename(filename: str) -> str:
    name = os.path.basename(filename or "document")
    name = name.strip().replace(" ", "_")
    name = re.sub(r"[^A-Za-z0-9._-]+", "_", name)
    name = re.sub(r"_+", "_", name).strip("._")
    if not name:
        raise APIError("UNSAFE_FILENAME", "The uploaded file name is invalid.", 400)
    return name


def _resolve_file_type(filename: str, mime_type: str) -> tuple[DocumentFileType, str]:
    ext = PurePosixPath(filename).suffix.lower()
    if ext not in ALLOWED_TYPES:
        raise APIError("UNSUPPORTED_FILE_TYPE", "Unsupported file type.", 400)
    expected_type, expected_mime = ALLOWED_TYPES[ext]
    if mime_type not in ALLOWED_MIME_TYPES:
        raise APIError("UNSUPPORTED_MIME_TYPE", "Unsupported document MIME type.", 400)
    if mime_type != expected_mime and mime_type not in {expected_mime, "text/x-markdown"}:
        raise APIError("MIME_TYPE_MISMATCH", "The uploaded file does not match the file type.", 400)
    return expected_type, expected_mime


@router.post("", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
async def create_document(
    title: Annotated[str, Form(...)],
    file: Annotated[UploadFile, File(...)],
    profile: Annotated[Profile, Depends(get_current_profile)],
    session: Annotated[Session, Depends(get_db)],
    storage: Annotated[SupabaseStorageAdapter, Depends(get_storage_adapter)],
) -> DocumentResponse:
    if not title or not title.strip():
        raise APIError("INVALID_TITLE", "The document title is required.", 400)
    if file is None:
        raise APIError("MISSING_FILE", "A document file is required.", 400)

    content = await file.read()
    if not content:
        raise APIError("EMPTY_FILE", "The uploaded file is empty.", 400)

    settings = get_settings()
    if len(content) > settings.max_document_size_bytes:
        raise APIError("FILE_TOO_LARGE", "The uploaded file exceeds the maximum allowed size.", 400)

    file_name = _safe_filename(file.filename or "document")
    file_type, mime_type = _resolve_file_type(file_name, (file.content_type or "application/octet-stream").lower())

    checksum = hashlib.sha256(content).hexdigest()
    existing = session.execute(
        select(Document).where(
            Document.uploaded_by == profile.id,
            Document.checksum_sha256 == checksum,
            Document.status != DocumentStatus.ARCHIVED,
        )
    ).scalar_one_or_none()
    if existing is not None:
        raise APIError("DOCUMENT_ALREADY_EXISTS", "This document has already been uploaded for this user.", 409)

    document_id = uuid4()
    sanitized_filename = _safe_filename(file_name)
    storage_path = f"{profile.id}/{document_id}/{sanitized_filename}"
    document = Document(
        id=document_id,
        title=title.strip(),
        original_filename=sanitized_filename,
        storage_bucket=settings.supabase_storage_bucket,
        storage_path=storage_path,
        file_type=file_type,
        mime_type=mime_type,
        file_size_bytes=len(content),
        checksum_sha256=checksum,
        status=DocumentStatus.PENDING,
        uploaded_by=profile.id,
    )
    try:
        session.add(document)
        session.commit()
        session.refresh(document)
    except Exception as exc:
        raise APIError("DOCUMENT_CREATE_FAILED", "The document could not be created.", 500) from exc

    try:
        await storage.upload_object(
            bucket=settings.supabase_storage_bucket,
            path=storage_path,
            data=content,
            content_type=mime_type,
        )
    except APIError:
        session.delete(document)
        session.commit()
        raise
    except Exception as exc:
        session.delete(document)
        session.commit()
        raise APIError("STORAGE_UPLOAD_FAILED", "The document could not be uploaded.", 502) from exc

    return DocumentResponse.model_validate(document)


def _owned_document(session: Session, document_id: UUID, profile: Profile) -> Document:
    document = session.execute(
        select(Document).where(Document.id == document_id, Document.uploaded_by == profile.id)
    ).scalar_one_or_none()
    if document is None:
        raise APIError("DOCUMENT_NOT_FOUND", "Document not found.", 404)
    return document


def _reject_archived(document: Document) -> None:
    if document.status == DocumentStatus.ARCHIVED:
        raise APIError("DOCUMENT_ARCHIVED", "Archived documents cannot be processed.", 409)


async def _process_document(
    document_id: UUID,
    profile: Profile,
    session: Session,
    storage: SupabaseStorageAdapter,
) -> DocumentResponse:
    document = _owned_document(session, document_id, profile)
    _reject_archived(document)
    if document.status == DocumentStatus.PROCESSING:
        raise APIError("DOCUMENT_ALREADY_PROCESSING", "The document is already being processed.", 409)

    locked = session.execute(
        select(Document).where(Document.id == document_id).with_for_update()
    ).scalar_one()
    if locked.status == DocumentStatus.PROCESSING:
        raise APIError("DOCUMENT_ALREADY_PROCESSING", "The document is already being processed.", 409)
    _reject_archived(locked)
    locked.status = DocumentStatus.PROCESSING
    locked.error_message = None
    session.commit()

    try:
        await ingest_document(session, locked, storage)
    except Exception as exc:
        raise APIError("DOCUMENT_PROCESSING_FAILED", "The document could not be processed.", 422) from exc
    session.refresh(locked)
    return DocumentResponse.model_validate(locked)


@router.get("", response_model=DocumentListResponse)
def list_documents(
    profile: Annotated[Profile, Depends(get_current_profile)],
    session: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    search: str | None = None,
    document_status: Annotated[DocumentStatus | None, Query(alias="status")] = None,
    file_type: DocumentFileType | None = None,
) -> DocumentListResponse:
    filters = [Document.uploaded_by == profile.id]
    if search and search.strip():
        pattern = f"%{search.strip()}%"
        filters.append(or_(Document.title.ilike(pattern), Document.original_filename.ilike(pattern)))
    if document_status is not None:
        filters.append(Document.status == document_status)
    if file_type is not None:
        filters.append(Document.file_type == file_type)
    total = session.scalar(select(func.count()).select_from(Document).where(*filters)) or 0
    items = session.scalars(
        select(Document)
        .where(*filters)
        .order_by(Document.created_at.desc(), Document.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return DocumentListResponse(
        items=[DocumentResponse.model_validate(item) for item in items],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.get("/{document_id}/chunks", response_model=DocumentChunkListResponse)
def list_document_chunks(
    document_id: UUID,
    profile: Annotated[Profile, Depends(get_current_profile)],
    session: Annotated[Session, Depends(get_db)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> DocumentChunkListResponse:
    document = _owned_document(session, document_id, profile)
    filters = [DocumentChunk.document_id == document.id]
    total = session.scalar(select(func.count()).select_from(DocumentChunk).where(*filters)) or 0
    chunks = session.scalars(
        select(DocumentChunk)
        .where(*filters)
        .order_by(DocumentChunk.chunk_index.asc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return DocumentChunkListResponse(
        items=[DocumentChunkResponse.model_validate(chunk) for chunk in chunks],
        page=page,
        page_size=page_size,
        total=total,
    )


@router.post("/{document_id}/process", response_model=DocumentResponse)
async def process_document(
    document_id: UUID,
    profile: Annotated[Profile, Depends(get_current_profile)],
    session: Annotated[Session, Depends(get_db)],
    storage: Annotated[SupabaseStorageAdapter, Depends(get_storage_adapter)],
) -> DocumentResponse:
    return await _process_document(document_id, profile, session, storage)


@router.post("/{document_id}/reprocess", response_model=DocumentResponse)
async def reprocess_document(
    document_id: UUID,
    profile: Annotated[Profile, Depends(get_current_profile)],
    session: Annotated[Session, Depends(get_db)],
    storage: Annotated[SupabaseStorageAdapter, Depends(get_storage_adapter)],
) -> DocumentResponse:
    return await _process_document(document_id, profile, session, storage)


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(
    document_id: UUID,
    profile: Annotated[Profile, Depends(get_current_profile)],
    session: Annotated[Session, Depends(get_db)],
) -> DocumentResponse:
    return DocumentResponse.model_validate(_owned_document(session, document_id, profile))


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_document(
    document_id: UUID,
    profile: Annotated[Profile, Depends(get_current_profile)],
    session: Annotated[Session, Depends(get_db)],
    storage: Annotated[SupabaseStorageAdapter, Depends(get_storage_adapter)],
) -> Response:
    document = _owned_document(session, document_id, profile)
    storage_bucket = document.storage_bucket
    storage_path = document.storage_path
    try:
        session.delete(document)
        session.flush()
    except Exception as exc:
        session.rollback()
        raise APIError("DOCUMENT_DELETE_FAILED", "The document could not be deleted.", 500) from exc
    try:
        await storage.delete_object(bucket=storage_bucket, path=storage_path)
    except APIError:
        session.rollback()
        raise
    except Exception as exc:
        session.rollback()
        raise APIError("STORAGE_DELETE_FAILED", "The document could not be deleted.", 502) from exc
    try:
        session.commit()
    except Exception as exc:
        session.rollback()
        raise APIError("DOCUMENT_DELETE_FAILED", "The document could not be deleted.", 500) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
