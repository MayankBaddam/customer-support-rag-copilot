import json
import logging
from typing import Annotated

import pytest
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.testclient import TestClient
from sqlalchemy.exc import SQLAlchemyError

from app.core.errors import APIError, register_exception_handlers
from app.core.logging import JsonFormatter, register_request_logging


@pytest.fixture
def error_app():
    application = FastAPI()
    register_request_logging(application)
    register_exception_handlers(application)

    @application.get("/http/{status_code}")
    def http_error(status_code: int):
        raise HTTPException(status_code=status_code, detail="private detail must not escape")

    @application.get("/validate")
    def validation_error(value: Annotated[int, Query(gt=0)]):
        return {"value": value}

    @application.get("/provider")
    def provider_error():
        raise APIError("PROVIDER_QUOTA_EXCEEDED", "The provider quota was exceeded.", 429)

    @application.get("/database")
    def database_error():
        raise SQLAlchemyError("postgresql://user:password@private-host/database")

    @application.get("/unexpected")
    def unexpected_error():
        raise RuntimeError("secret-token unexpected detail")

    @application.post("/observe")
    async def observed_request(_: Request):
        return {"status": "ok"}

    return application


@pytest.mark.parametrize(
    ("path", "expected_status", "expected_code"),
    [
        ("/http/400", 400, "BAD_REQUEST"),
        ("/http/401", 401, "AUTHENTICATION_REQUIRED"),
        ("/http/403", 403, "ACCESS_FORBIDDEN"),
        ("/missing", 404, "NOT_FOUND"),
        ("/validate?value=0", 422, "VALIDATION_ERROR"),
        ("/provider", 429, "PROVIDER_QUOTA_EXCEEDED"),
    ],
)
def test_client_error_categories_use_consistent_json(error_app, path, expected_status, expected_code):
    with TestClient(error_app) as client:
        response = client.get(path)

    assert response.status_code == expected_status
    assert set(response.json()) == {"error"}
    assert set(response.json()["error"]) == {"code", "message", "request_id"}
    assert response.json()["error"]["code"] == expected_code
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]
    assert "private detail" not in response.text


@pytest.mark.parametrize(
    ("path", "expected_code"),
    [("/database", "DATABASE_ERROR"), ("/unexpected", "INTERNAL_SERVER_ERROR")],
)
def test_server_error_categories_are_safe_json(error_app, path, expected_code):
    with TestClient(error_app, raise_server_exceptions=False) as client:
        response = client.get(path)

    assert response.status_code == 500
    assert response.json()["error"]["code"] == expected_code
    assert response.json()["error"]["request_id"]
    assert "password" not in response.text
    assert "secret-token" not in response.text


def test_request_logs_include_metadata_latency_and_no_sensitive_values(error_app, caplog):
    caplog.set_level(logging.INFO, logger="app.requests")
    with TestClient(error_app) as client:
        response = client.post(
            "/observe?password=private-password",
            headers={"Authorization": "Bearer private-access-token", "X-API-Key": "private-api-key"},
            json={
                "prompt": "private prompt",
                "embedding": [0.1, 0.2],
                "content": "complete private document content",
            },
        )
        failed = client.get("/provider")

    request_records = [record for record in caplog.records if record.name == "app.requests"]
    events = [record.event for record in request_records]
    assert response.status_code == 200
    assert failed.status_code == 429
    assert "request_start" in events
    assert "request_complete" in events
    assert "request_failure" in events
    completion = next(record for record in request_records if record.event == "request_complete")
    assert completion.request_method == "POST"
    assert completion.request_path == "/observe"
    assert completion.status_code == 200
    assert completion.latency_ms >= 0
    formatter = JsonFormatter()
    structured_completion = json.loads(formatter.format(completion))
    assert structured_completion["event"] == "request_complete"
    assert structured_completion["request_id"] == response.headers["x-request-id"]
    assert structured_completion["latency_ms"] >= 0
    rendered_logs = "\n".join(formatter.format(record) for record in request_records)
    for sensitive_value in (
        "private-password",
        "private-access-token",
        "private-api-key",
        "private prompt",
        "0.1",
        "complete private document content",
    ):
        assert sensitive_value not in rendered_logs
