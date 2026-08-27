from __future__ import annotations

import hashlib
import os
import re
from pathlib import PurePosixPath
from typing import Annotated
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_profile
from app.database.session import get_db
from app.core.config import get_settings
from app.core.errors import APIError
from app.models import Document, DocumentFileType, DocumentStatus, Profile
from app.schemas.documents import DocumentResponse
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
