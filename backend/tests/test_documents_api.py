import io
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_profile, get_db
from app.core.errors import APIError
from app.main import app
from app.models import Base, Document, DocumentStatus, Profile, ProfileRole
from app.services.storage import SupabaseStorageAdapter


class MockStorage(SupabaseStorageAdapter):
    def __init__(self, *, fail_upload=False):
        self.fail_upload = fail_upload
        self.uploaded = []
        self.deleted = []

    async def upload_object(self, *, bucket: str, path: str, data: bytes, content_type: str) -> None:
        if self.fail_upload:
            raise APIError("STORAGE_UPLOAD_FAILED", "The document could not be uploaded.", 502)
        self.uploaded.append({"bucket": bucket, "path": path, "size": len(data), "content_type": content_type})

    async def delete_object(self, *, bucket: str, path: str) -> None:
        self.deleted.append({"bucket": bucket, "path": path})

    async def download_object(self, *, bucket: str, path: str) -> bytes:
        return b"downloaded"


@pytest.fixture
def document_api_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    profile = Profile(id=uuid4(), full_name="API Document Agent", role=ProfileRole.AGENT)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        session.add(profile)
        session.commit()

    def override_db():
        with session_factory() as session:
            yield session

    def override_profile():
        return profile

    storage = MockStorage()
    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_profile] = override_profile

    from app.api.v1.documents import get_storage_adapter

    app.dependency_overrides[get_storage_adapter] = lambda: storage
    with TestClient(app) as client:
        yield client, profile, storage, session_factory
    app.dependency_overrides.clear()
    engine.dispose()


def make_pdf_bytes() -> bytes:
    return b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\ntrailer\n<<>>\n%%EOF"


def test_document_upload_success_pdf(document_api_client):
    client, _, storage, _ = document_api_client
    response = client.post(
        "/api/v1/documents",
        data={"title": "Refund policy"},
        files={"file": ("../Refund Policy.pdf", make_pdf_bytes(), "application/pdf")},
    )

    assert response.status_code == 201, response.text
    data = response.json()
    assert data["title"] == "Refund policy"
    assert data["original_filename"] == "Refund_Policy.pdf"
    assert data["file_type"] == "pdf"
    assert data["status"] == "pending"
    assert len(storage.uploaded) == 1
    assert storage.uploaded[0]["bucket"] == "knowledge-documents"
    assert storage.uploaded[0]["path"].startswith(f"{str(data['uploaded_by'])}/")
    assert "storage_path" not in data
    assert "error_message" not in data


def test_document_upload_success_markdown(document_api_client):
    client, _, _, _ = document_api_client
    response = client.post(
        "/api/v1/documents",
        data={"title": "Support guide"},
        files={"file": ("guide.md", b"# Guide\n\nThis is a markdown guide.", "text/markdown")},
    )

    assert response.status_code == 201, response.text
    assert response.json()["file_type"] == "markdown"
    assert response.json()["mime_type"] == "text/markdown"


def test_document_upload_success_txt(document_api_client):
    client, _, _, _ = document_api_client
    response = client.post(
        "/api/v1/documents",
        data={"title": "Simple notes"},
        files={"file": ("notes.txt", b"hello from plain text", "text/plain")},
    )

    assert response.status_code == 201, response.text
    assert response.json()["file_type"] == "text"
    assert response.json()["mime_type"] == "text/plain"


def test_document_upload_requires_authentication():
    app.dependency_overrides.clear()
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/documents",
            data={"title": "Unauthenticated"},
            files={"file": ("secret.pdf", make_pdf_bytes(), "application/pdf")},
        )

    assert response.status_code in {401, 403}


def test_document_upload_rejects_empty_file(document_api_client):
    client, _, _, _ = document_api_client
    response = client.post(
        "/api/v1/documents",
        data={"title": "Empty file"},
        files={"file": ("empty.pdf", b"", "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "EMPTY_FILE"


def test_document_upload_rejects_oversized_file(document_api_client):
    client, _, _, _ = document_api_client
    from app.core.config import get_settings

    settings = get_settings()
    huge = b"A" * (settings.max_document_size_bytes + 1)
    response = client.post(
        "/api/v1/documents",
        data={"title": "Too big"},
        files={"file": ("too-big.pdf", huge, "application/pdf")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "FILE_TOO_LARGE"


def test_document_upload_rejects_unsupported_extension(document_api_client):
    client, _, _, _ = document_api_client
    response = client.post(
        "/api/v1/documents",
        data={"title": "Wrong extension"},
        files={"file": ("notes.doc", b"not a pdf", "application/octet-stream")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNSUPPORTED_FILE_TYPE"


def test_document_upload_rejects_mismatched_mime_type(document_api_client):
    client, _, _, _ = document_api_client
    response = client.post(
        "/api/v1/documents",
        data={"title": "Mismatched MIME"},
        files={"file": ("notes.pdf", b"%PDF-1.4", "text/plain")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "MIME_TYPE_MISMATCH"


def test_document_upload_sanitizes_unsafe_filename(document_api_client):
    client, _, _, _ = document_api_client
    response = client.post(
        "/api/v1/documents",
        data={"title": "Sanitized title"},
        files={"file": ("../../weird name?.pdf", make_pdf_bytes(), "application/pdf")},
    )

    assert response.status_code == 201, response.text
    assert response.json()["original_filename"] == "weird_name_.pdf"


def test_document_upload_rejects_duplicate_checksum_for_same_user(document_api_client):
    client, _, _, _ = document_api_client
    response = client.post(
        "/api/v1/documents",
        data={"title": "Duplicate file"},
        files={"file": ("duplicate.pdf", make_pdf_bytes(), "application/pdf")},
    )
    assert response.status_code == 201, response.text

    second = client.post(
        "/api/v1/documents",
        data={"title": "Duplicate file second"},
        files={"file": ("duplicate-copy.pdf", make_pdf_bytes(), "application/pdf")},
    )

    assert second.status_code == 409
    assert second.json()["error"]["code"] == "DOCUMENT_ALREADY_EXISTS"


def test_document_upload_allows_same_checksum_for_different_user(document_api_client):
    client, profile, _, session_factory = document_api_client
    other_profile = Profile(id=uuid4(), full_name="Other User", role=ProfileRole.AGENT)
    with session_factory() as session:
        session.add(other_profile)
        session.commit()

    app.dependency_overrides[get_current_profile] = lambda: other_profile
    try:
        response = client.post(
            "/api/v1/documents",
            data={"title": "Other user upload"},
            files={"file": ("duplicate-other-user.pdf", make_pdf_bytes(), "application/pdf")},
        )
    finally:
        app.dependency_overrides[get_current_profile] = lambda: profile

    assert response.status_code == 201, response.text
    assert response.json()["uploaded_by"] == str(other_profile.id)


def test_storage_upload_failure_removes_database_record(document_api_client):
    client, _, storage, session_factory = document_api_client
    storage.fail_upload = True
    response = client.post(
        "/api/v1/documents",
        data={"title": "Failing upload"},
        files={"file": ("fail.pdf", make_pdf_bytes(), "application/pdf")},
    )

    assert response.status_code == 502
    with session_factory() as session:
        assert session.query(Document).count() == 0


def test_document_upload_returns_safe_error_payload(document_api_client):
    client, _, storage, _ = document_api_client
    storage.fail_upload = True
    response = client.post(
        "/api/v1/documents",
        data={"title": "Leaky error"},
        files={"file": ("fail.pdf", make_pdf_bytes(), "application/pdf")},
    )

    payload = response.json()
    assert payload["error"]["code"] == "STORAGE_UPLOAD_FAILED"
    assert payload["error"]["message"] == "The document could not be uploaded."
    assert "secret" not in str(payload).lower()
    assert "supabase" not in str(payload).lower()
