from uuid import uuid4

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_user, get_db
from app.main import app
from app.models import Base
from app.services.auth import AuthenticatedUser


def test_missing_token_returns_401(client):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_invalid_token_returns_401(client, monkeypatch):
    async def reject_token(_token):
        raise ValueError("invalid")

    monkeypatch.setattr("app.api.dependencies.verify_access_token", reject_token)
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalid"})

    assert response.status_code == 401


def test_valid_token_returns_current_profile(client, monkeypatch):
    user_id = uuid4()

    async def accept_token(_token):
        return AuthenticatedUser(id=user_id, email="agent@example.test", full_name="Demo Agent")

    monkeypatch.setattr("app.api.dependencies.verify_access_token", accept_token)
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)

    def override_db():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_db
    try:
        response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer valid"})
    finally:
        app.dependency_overrides.clear()
        engine.dispose()

    assert response.status_code == 200
    assert response.json() == {"id": str(user_id), "full_name": "Demo Agent", "role": "agent"}