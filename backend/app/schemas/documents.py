from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import DocumentFileType, DocumentStatus


class DocumentCreate(BaseModel):
    title: str = Field(min_length=1, max_length=240)
    original_filename: str = Field(min_length=1, max_length=255)
    storage_bucket: str = Field(min_length=1, max_length=128)
    storage_path: str = Field(min_length=1, max_length=1024)
    file_type: DocumentFileType
    mime_type: str = Field(min_length=1, max_length=128)
    file_size_bytes: int = Field(gt=0)
    checksum_sha256: str = Field(min_length=1, max_length=128)
    status: DocumentStatus = DocumentStatus.PENDING
    version: int = Field(default=1, gt=0)
    chunk_count: int = Field(default=0, ge=0)
    uploaded_by: UUID | None = None


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    original_filename: str
    storage_bucket: str
    file_type: DocumentFileType
    mime_type: str
    file_size_bytes: int
    checksum_sha256: str
    status: DocumentStatus
    version: int
    chunk_count: int
    uploaded_by: UUID | None
    created_at: datetime
    updated_at: datetime
    processed_at: datetime | None


class DocumentChunkCreate(BaseModel):
    chunk_index: int = Field(ge=0)
    content: str
    section_title: str | None = Field(default=None, max_length=240)
    page_number: int | None = Field(default=None, gt=0)
    token_count: int = Field(ge=0)
    metadata: dict = Field(default_factory=dict)


class DocumentChunkResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    document_id: UUID
    chunk_index: int
    content: str
    section_title: str | None
    page_number: int | None
    token_count: int
    metadata: dict
    created_at: datetime
