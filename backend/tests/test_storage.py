import asyncio
from unittest.mock import AsyncMock

import httpx
import pytest

from app.core.config import get_settings
from app.core.errors import APIError
from app.services.storage import SupabaseStorageAdapter


@pytest.fixture
def storage_settings(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", "https://project.example")
    monkeypatch.setenv("SUPABASE_SECRET_KEY", "sb_secret_test")
    monkeypatch.setenv("SUPABASE_STORAGE_BUCKET", "private-documents")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_storage_adapter_supports_upload_download_and_delete_with_opaque_key(storage_settings):
    client = AsyncMock(spec=httpx.AsyncClient)
    client.post.return_value = httpx.Response(200)
    client.get.return_value = httpx.Response(200, content=b"document")
    client.delete.return_value = httpx.Response(200)
    adapter = SupabaseStorageAdapter(client)

    asyncio.run(adapter.upload_object(bucket="private-documents", path="user/doc/file.txt", data=b"document", content_type="text/plain"))
    assert asyncio.run(adapter.download_object(bucket="private-documents", path="user/doc/file.txt")) == b"document"
    asyncio.run(adapter.delete_object(bucket="private-documents", path="user/doc/file.txt"))

    for call in (client.post.call_args, client.get.call_args, client.delete.call_args):
        assert call.kwargs["headers"] == {"apikey": "sb_secret_test"}


def test_storage_provider_errors_are_safe(storage_settings):
    client = AsyncMock(spec=httpx.AsyncClient)
    client.get.side_effect = httpx.ConnectError("provider detail")
    adapter = SupabaseStorageAdapter(client)

    with pytest.raises(APIError) as caught:
        asyncio.run(adapter.download_object(bucket="private-documents", path="user/doc/file.txt"))

    assert caught.value.code == "STORAGE_DOWNLOAD_FAILED"
    assert caught.value.message == "The document could not be downloaded."
    assert "provider detail" not in caught.value.message


def test_storage_delete_is_idempotent_when_object_is_already_missing(storage_settings):
    client = AsyncMock(spec=httpx.AsyncClient)
    client.delete.return_value = httpx.Response(
        400,
        json={"statusCode": "404", "error": "not_found", "message": "Object not found", "code": "NoSuchKey"},
    )
    adapter = SupabaseStorageAdapter(client)

    asyncio.run(adapter.delete_object(bucket="private-documents", path="user/doc/missing.txt"))
