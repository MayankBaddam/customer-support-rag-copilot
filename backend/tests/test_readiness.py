import pytest


def test_readiness_returns_connected_when_database_check_succeeds(client):
    async def successful_check():
        return {"application": "ok", "database": "connected"}

    original_check = client.app.state.readiness_check
    client.app.state.readiness_check = successful_check
    try:
        response = client.get("/api/v1/ready")
    finally:
        client.app.state.readiness_check = original_check

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "checks": {"application": "ok", "database": "connected"},
    }


@pytest.mark.anyio
async def test_readiness_returns_503_when_dependency_fails(client):
    async def failing_check():
        raise RuntimeError("dependency unavailable")

    original_check = client.app.state.readiness_check
    client.app.state.readiness_check = failing_check
    try:
        response = client.get("/api/v1/ready")
    finally:
        client.app.state.readiness_check = original_check

    assert response.status_code == 503
    assert response.json() == {
        "error": {
            "code": "DEPENDENCY_UNAVAILABLE",
            "message": "A required dependency is unavailable.",
        }
    }