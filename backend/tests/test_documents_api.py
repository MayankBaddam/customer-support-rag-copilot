import io
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_profile, get_db
from app.core.errors import APIError
from app.main import app
from app.models import Base, Document, DocumentChunk, DocumentStatus, Profile, ProfileRole
from app.services.storage import SupabaseStorageAdapter


class MockEmbeddingProvider:
    def __init__(self):
        self.calls = []

    def embed_texts(self, texts):
        self.calls.append(list(texts))
        return [[0.25] * 768 for _ in texts]

    def embed_query(self, _text):
        raise AssertionError("query embedding is outside this task")


class MockStorage(SupabaseStorageAdapter):
    def __init__(self, *, fail_upload=False, fail_download=False, fail_delete=False):
        self.fail_upload = fail_upload
        self.fail_download = fail_download
        self.fail_delete = fail_delete
        self.download_content = b"downloaded"
        self.uploaded = []
        self.deleted = []

    async def upload_object(self, *, bucket: str, path: str, data: bytes, content_type: str) -> None:
        if self.fail_upload:
            raise APIError("STORAGE_UPLOAD_FAILED", "The document could not be uploaded.", 502)
        self.uploaded.append({"bucket": bucket, "path": path, "size": len(data), "content_type": content_type})

    async def delete_object(self, *, bucket: str, path: str) -> None:
        if self.fail_delete:
            raise APIError("STORAGE_DELETE_FAILED", "The document could not be deleted.", 502)
        self.deleted.append({"bucket": bucket, "path": path})

    async def download_object(self, *, bucket: str, path: str) -> bytes:
        if self.fail_download:
            raise APIError("STORAGE_DOWNLOAD_FAILED", "The document could not be downloaded.", 502)
        return self.download_content


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


def test_document_upload_rejects_non_allowlisted_markdown_mime_type(document_api_client):
    client, _, _, _ = document_api_client
    response = client.post(
        "/api/v1/documents",
        data={"title": "Legacy Markdown MIME"},
        files={"file": ("notes.md", b"# Notes", "text/x-markdown")},
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "UNSUPPORTED_MIME_TYPE"


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


def _upload_text(client, title="Guide", content=b"first paragraph\n\nsecond paragraph"):
    return client.post(
        "/api/v1/documents",
        data={"title": title},
        files={"file": (f"{title}.txt", content, "text/plain")},
    )


def test_document_processing_completes_and_is_idempotent(document_api_client):
    client, _, storage, session_factory = document_api_client
    created = _upload_text(client)
    document_id = created.json()["id"]

    processed = client.post(f"/api/v1/documents/{document_id}/process")
    assert processed.status_code == 200, processed.text
    assert processed.json()["status"] == "completed"
    assert processed.json()["chunk_count"] == 1

    reprocessed = client.post(f"/api/v1/documents/{document_id}/reprocess")
    assert reprocessed.status_code == 200
    with session_factory() as session:
        document = session.get(Document, UUID(document_id))
        assert document.chunk_count == 1
        assert session.query(DocumentChunk).filter_by(document_id=UUID(document_id)).count() == 1
    assert storage.deleted == []


def test_document_processing_failure_sets_failed_and_can_recover(document_api_client):
    client, _, storage, session_factory = document_api_client
    document_id = _upload_text(client).json()["id"]
    storage.fail_download = True

    failed = client.post(f"/api/v1/documents/{document_id}/process")
    assert failed.status_code == 422
    with session_factory() as session:
        document = session.get(Document, UUID(document_id))
        assert document.status == DocumentStatus.FAILED
        assert document.error_message == "Document storage operation failed."

    storage.fail_download = False
    recovered = client.post(f"/api/v1/documents/{document_id}/reprocess")
    assert recovered.status_code == 200
    assert recovered.json()["status"] == "completed"


def test_document_processing_rejects_archived_and_concurrent_states(document_api_client):
    client, _, _, session_factory = document_api_client
    document_id = _upload_text(client).json()["id"]
    with session_factory() as session:
        document = session.get(Document, UUID(document_id))
        document.status = DocumentStatus.ARCHIVED
        session.commit()
    archived = client.post(f"/api/v1/documents/{document_id}/process")
    assert archived.status_code == 409
    assert archived.json()["error"]["code"] == "DOCUMENT_ARCHIVED"

    with session_factory() as session:
        document = session.get(Document, UUID(document_id))
        document.status = DocumentStatus.PROCESSING
        session.commit()
    concurrent = client.post(f"/api/v1/documents/{document_id}/process")
    assert concurrent.status_code == 409
    assert concurrent.json()["error"]["code"] == "DOCUMENT_ALREADY_PROCESSING"


def test_document_list_filters_searches_and_paginates(document_api_client):
    client, _, _, _ = document_api_client
    _upload_text(client, "Alpha manual")
    _upload_text(client, "Beta notes", b"different")

    response = client.get("/api/v1/documents", params={"search": "alpha", "page": 1, "page_size": 1})
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["title"] == "Alpha manual"


def test_document_chunks_are_paginated_and_ordered(document_api_client):
    client, _, _, _ = document_api_client
    document_id = _upload_text(client).json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/process").status_code == 200

    response = client.get(f"/api/v1/documents/{document_id}/chunks", params={"page_size": 1})
    assert response.status_code == 200
    assert response.json()["total"] == 1
    assert response.json()["items"][0]["chunk_index"] == 0
    assert response.json()["items"][0]["token_count"] > 0
    assert "embedding" not in response.json()["items"][0]


def test_document_delete_removes_storage_row_and_chunks(document_api_client):
    client, _, storage, session_factory = document_api_client
    document_id = _upload_text(client).json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/process").status_code == 200

    deleted = client.delete(f"/api/v1/documents/{document_id}")
    assert deleted.status_code == 204
    assert len(storage.deleted) == 1
    with session_factory() as session:
        assert session.get(Document, UUID(document_id)) is None
        assert session.query(DocumentChunk).filter_by(document_id=UUID(document_id)).count() == 0


def test_document_delete_storage_failure_preserves_database(document_api_client):
    client, _, storage, session_factory = document_api_client
    document_id = _upload_text(client).json()["id"]
    storage.fail_delete = True

    response = client.delete(f"/api/v1/documents/{document_id}")
    assert response.status_code == 502
    assert response.json()["error"]["code"] == "STORAGE_DELETE_FAILED"
    with session_factory() as session:
        assert session.get(Document, UUID(document_id)) is not None


def test_document_delete_database_failure_does_not_remove_storage(document_api_client, monkeypatch):
    client, _, storage, session_factory = document_api_client
    document_id = _upload_text(client).json()["id"]

    def fail_delete(_session, _document):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(Session, "delete", fail_delete)
    response = client.delete(f"/api/v1/documents/{document_id}")

    assert response.status_code == 500
    assert response.json()["error"]["code"] == "DOCUMENT_DELETE_FAILED"
    assert storage.deleted == []
    monkeypatch.undo()
    with session_factory() as session:
        assert session.get(Document, UUID(document_id)) is not None


def test_document_management_requires_owner(document_api_client):
    client, _, _, _ = document_api_client
    document_id = _upload_text(client).json()["id"]
    from app.api.v1.documents import get_current_profile

    other = Profile(id=uuid4(), full_name="Other", role=ProfileRole.AGENT)
    app.dependency_overrides[get_current_profile] = lambda: other
    try:
        listed = client.get("/api/v1/documents")
        assert listed.status_code == 200
        assert listed.json()["items"] == []
        assert client.get(f"/api/v1/documents/{document_id}").status_code == 404
        assert client.get(f"/api/v1/documents/{document_id}/chunks").status_code == 404
        assert client.post(f"/api/v1/documents/{document_id}/process").status_code == 404
        assert client.delete(f"/api/v1/documents/{document_id}").status_code == 404
    finally:
        app.dependency_overrides.pop(get_current_profile, None)


def test_document_content_is_not_logged(document_api_client, caplog):
    client, _, _, _ = document_api_client
    private_content = b"phase-five-private-document-marker"

    response = client.post(
        "/api/v1/documents",
        data={"title": "Logging check"},
        files={"file": ("logging-check.txt", private_content, "text/plain")},
    )

    assert response.status_code == 201
    assert private_content.decode() not in caplog.text


def test_document_embedding_endpoint_processes_completed_owner_document(document_api_client):
    client, _, _, session_factory = document_api_client
    document_id = _upload_text(client).json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/process").status_code == 200
    provider = MockEmbeddingProvider()
    from app.api.v1.documents import get_embedding_provider

    app.dependency_overrides[get_embedding_provider] = lambda: provider
    response = client.post(f"/api/v1/documents/{document_id}/embed")

    assert response.status_code == 200
    assert response.json() == {"processed": 1, "skipped": 0, "failed": 0, "status": "completed"}
    assert len(provider.calls) == 1
    assert "embedding" not in response.text
    with session_factory() as session:
        chunk = session.query(DocumentChunk).filter_by(document_id=UUID(document_id)).one()
        assert len(chunk.embedding) == 768


def test_document_embedding_endpoint_requires_owner(document_api_client):
    client, profile, _, _ = document_api_client
    document_id = _upload_text(client).json()["id"]
    assert client.post(f"/api/v1/documents/{document_id}/process").status_code == 200
    provider = MockEmbeddingProvider()
    other = Profile(id=uuid4(), full_name="Other", role=ProfileRole.AGENT)
    from app.api.v1.documents import get_embedding_provider

    app.dependency_overrides[get_embedding_provider] = lambda: provider
    app.dependency_overrides[get_current_profile] = lambda: other
    try:
        response = client.post(f"/api/v1/documents/{document_id}/embed")
    finally:
        app.dependency_overrides[get_current_profile] = lambda: profile

    assert response.status_code == 404
    assert provider.calls == []


@pytest.mark.parametrize("document_status", [DocumentStatus.PENDING, DocumentStatus.ARCHIVED])
def test_document_embedding_endpoint_rejects_non_completed_documents(document_api_client, document_status):
    client, _, _, session_factory = document_api_client
    document_id = _upload_text(client).json()["id"]
    with session_factory() as session:
        document = session.get(Document, UUID(document_id))
        document.status = document_status
        session.commit()
    provider = MockEmbeddingProvider()
    from app.api.v1.documents import get_embedding_provider

    app.dependency_overrides[get_embedding_provider] = lambda: provider
    response = client.post(f"/api/v1/documents/{document_id}/embed")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "DOCUMENT_NOT_COMPLETED"
    assert provider.calls == []
