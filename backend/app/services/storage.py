from __future__ import annotations

from urllib.parse import quote

import httpx

from app.core.config import get_settings
from app.core.errors import APIError


class SupabaseStorageAdapter:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client or httpx.AsyncClient(timeout=15.0)
        self._settings = get_settings()

    async def upload_object(self, *, bucket: str, path: str, data: bytes, content_type: str) -> None:
        await self._request(
            method="post",
            bucket=bucket,
            path=path,
            data=data,
            content_type=content_type,
        )

    async def delete_object(self, *, bucket: str, path: str) -> None:
        await self._request(method="delete", bucket=bucket, path=path)

    async def download_object(self, *, bucket: str, path: str) -> bytes:
        response = await self._request(method="get", bucket=bucket, path=path, return_bytes=True)
        if isinstance(response, bytes):
            return response
        return b""

    async def _request(self, *, method: str, bucket: str, path: str, data: bytes | None = None, content_type: str | None = None, return_bytes: bool = False):
        operation = {"get": "download", "delete": "delete", "post": "upload"}.get(method, "storage")
        error_code = f"STORAGE_{operation.upper()}_FAILED"
        operation_message = {"download": "downloaded", "delete": "deleted", "upload": "uploaded"}.get(
            operation, "completed"
        )
        if not self._settings.supabase_url:
            raise APIError("STORAGE_CONFIG_ERROR", "Storage is not configured.", 500)
        if not self._settings.supabase_secret_key:
            raise APIError("STORAGE_CONFIG_ERROR", "Storage is not configured.", 500)

        encoded_path = quote(path, safe="/")
        url = f"{self._settings.supabase_url.rstrip('/')}/storage/v1/object/{bucket}/{encoded_path}"
        secret_key = self._settings.supabase_secret_key.get_secret_value()
        headers = {"apikey": secret_key}
        if not secret_key.startswith("sb_secret_"):
            headers["Authorization"] = f"Bearer {secret_key}"

        try:
            if method == "get":
                response = await self._client.get(url, headers=headers)
            elif method == "delete":
                response = await self._client.delete(url, headers=headers)
            else:
                response = await self._client.post(
                    url,
                    headers=headers,
                    files={"file": (path.rsplit("/", 1)[-1], data or b"", content_type or "application/octet-stream")},
                )
        except httpx.HTTPError as exc:
            raise APIError(error_code, f"The document could not be {operation_message}.", 502) from exc

        if method == "delete" and response.status_code >= 300:
            try:
                payload = response.json()
            except ValueError:
                payload = {}
            if payload.get("code") == "NoSuchKey" or str(payload.get("statusCode")) == "404":
                return None

        if response.status_code >= 300:
            raise APIError(error_code, f"The document could not be {operation_message}.", 502)

        if return_bytes:
            return response.content
        return None


def get_storage_adapter() -> SupabaseStorageAdapter:
    return SupabaseStorageAdapter()
