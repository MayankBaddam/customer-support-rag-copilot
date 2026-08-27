import logging
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

import app.api.dependencies as auth_dependencies
from app.api.dependencies import get_current_profile
from app.api.v1.copilot import get_answer_service, get_retrieval_service
from app.core.config import Settings
from app.main import app, create_app
from app.models import Profile, ProfileRole


def test_cors_accepts_only_configured_origins():
    settings = Settings(
        _env_file=None,
        CORS_ORIGINS="https://support.example.com,http://localhost:3000",
    )
    with TestClient(create_app(settings)) as client:
        allowed = client.options(
            "/api/v1/documents",
            headers={
                "Origin": "https://support.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        denied = client.options(
            "/api/v1/documents",
            headers={
                "Origin": "https://untrusted.example.com",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == "https://support.example.com"
    assert "access-control-allow-origin" not in denied.headers


def test_all_document_and_copilot_endpoints_require_authentication():
    app.dependency_overrides.clear()
    document_id = uuid4()
    requests = [
        ("get", "/api/v1/documents", {}),
        (
            "post",
            "/api/v1/documents",
            {
                "data": {"title": "Private"},
                "files": {"file": ("private.txt", b"private", "text/plain")},
            },
        ),
        ("get", f"/api/v1/documents/{document_id}", {}),
        ("get", f"/api/v1/documents/{document_id}/chunks", {}),
        ("post", f"/api/v1/documents/{document_id}/process", {}),
        ("post", f"/api/v1/documents/{document_id}/reprocess", {}),
        ("post", f"/api/v1/documents/{document_id}/embed", {}),
        ("delete", f"/api/v1/documents/{document_id}", {}),
        ("post", "/api/v1/copilot/search", {"json": {"query": "valid", "top_k": 5}}),
        ("post", "/api/v1/copilot/answer", {"json": {"query": "valid", "top_k": 5}}),
    ]

    with TestClient(app) as client:
        responses = [client.request(method, path, **kwargs) for method, path, kwargs in requests]

    assert [response.status_code for response in responses] == [401] * len(requests)


@pytest.mark.parametrize("endpoint", ["/api/v1/copilot/search", "/api/v1/copilot/answer"])
@pytest.mark.parametrize(
    "payload",
    [
        {"query": "", "top_k": 5},
        {"query": "   ", "top_k": 5},
        {"query": "x" * 1001, "top_k": 5},
        {"query": "valid", "top_k": 0},
        {"query": "valid", "top_k": 11},
    ],
)
def test_copilot_request_limits_return_422(endpoint, payload):
    profile = Profile(id=uuid4(), full_name="Security Agent", role=ProfileRole.AGENT)

    class MustNotRun:
        def search(self, *args, **kwargs):
            raise AssertionError("Search must not run for invalid input.")

        def answer(self, *args, **kwargs):
            raise AssertionError("Answer generation must not run for invalid input.")

    app.dependency_overrides[get_current_profile] = lambda: profile
    app.dependency_overrides[get_retrieval_service] = lambda: MustNotRun()
    app.dependency_overrides[get_answer_service] = lambda: MustNotRun()
    try:
        with TestClient(app) as client:
            response = client.post(endpoint, json=payload)
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "VALIDATION_ERROR"


def test_invalid_bearer_token_is_not_logged(monkeypatch, caplog):
    token = "phase-five-private-token-marker"

    async def reject_token(_token):
        raise ValueError("invalid token")

    monkeypatch.setattr(auth_dependencies, "verify_access_token", reject_token)
    caplog.set_level(logging.DEBUG)
    app.dependency_overrides.clear()
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/documents",
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 401
    assert token not in caplog.text
