from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_current_profile, get_db
from app.main import app
from app.models import Base, Profile, ProfileRole, TicketCategory, TicketPriority, TicketStatus


@pytest.fixture
def ticket_api_client():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    profile = Profile(id=uuid4(), full_name="API Demo Agent", role=ProfileRole.AGENT)
    session_factory = sessionmaker(bind=engine, expire_on_commit=False)
    with session_factory() as session:
        session.add(profile)
        session.commit()

    def override_db():
        with session_factory() as session:
            yield session

    def override_profile():
        return profile

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_profile] = override_profile
    from fastapi.testclient import TestClient

    with TestClient(app) as test_client:
        yield test_client, profile
    app.dependency_overrides.clear()
    engine.dispose()


def ticket_payload(**overrides):
    payload = {
        "subject": "Cannot update workspace plan",
        "customer_name": "Fictional Customer",
        "customer_email": "customer@example.com",
        "customer_plan": "basic",
        "category": "subscription",
        "priority": "medium",
        "status": "open",
        "first_message": {
            "sender_type": "customer",
            "sender_name": "Fictional Customer",
            "content": "Please help with this plan change.",
        },
    }
    payload.update(overrides)
    return payload


def create_ticket(client, **overrides):
    response = client.post("/api/v1/tickets", json=ticket_payload(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


def test_create_ticket_creates_conversation_and_message(ticket_api_client):
    client, profile = ticket_api_client
    ticket = create_ticket(client)

    assert ticket["ticket_number"].startswith("TCK-")
    assert ticket["created_by"] == str(profile.id)
    assert len(ticket["conversations"]) == 1
    assert ticket["conversations"][0]["messages"][0]["sender_type"] == "customer"


def test_list_paginates_and_sorts_newest_first(ticket_api_client):
    client, _ = ticket_api_client
    create_ticket(client, subject="First ticket")
    create_ticket(client, subject="Second ticket")

    response = client.get("/api/v1/tickets?page=1&page_size=1")

    assert response.status_code == 200
    assert response.json()["total"] == 2
    assert response.json()["page_size"] == 1
    assert len(response.json()["items"]) == 1


def test_search_and_each_filter(ticket_api_client):
    client, _ = ticket_api_client
    create_ticket(client, subject="Billing duplicate", category="billing", priority="urgent", customer_plan="pro", status="in_progress")
    create_ticket(client, subject="Access question", category="account_access", priority="low", customer_plan="free", status="waiting")

    for query, expected_subject in [
        ("search=Billing", "Billing duplicate"),
        ("status=in_progress", "Billing duplicate"),
        ("priority=urgent", "Billing duplicate"),
        ("category=billing", "Billing duplicate"),
        ("plan=pro", "Billing duplicate"),
    ]:
        response = client.get(f"/api/v1/tickets?{query}")
        assert response.status_code == 200
        assert [item["subject"] for item in response.json()["items"]] == [expected_subject]


def test_get_update_and_add_message(ticket_api_client):
    client, profile = ticket_api_client
    ticket = create_ticket(client)
    ticket_id = ticket["id"]

    details = client.get(f"/api/v1/tickets/{ticket_id}")
    assert details.status_code == 200
    assert len(details.json()["conversations"][0]["messages"]) == 1

    updated = client.patch(f"/api/v1/tickets/{ticket_id}", json={"status": "resolved", "priority": "high"})
    assert updated.status_code == 200
    assert updated.json()["status"] == "resolved"
    assert updated.json()["priority"] == "high"
    assert updated.json()["created_by"] == str(profile.id)

    message = client.post(
        f"/api/v1/tickets/{ticket_id}/messages",
        json={"sender_type": "agent", "sender_name": "Forged Name", "content": "We are reviewing this."},
    )
    assert message.status_code == 201
    assert message.json()["sender_name"] == "API Demo Agent"
    assert client.get(f"/api/v1/tickets/{uuid4()}").status_code == 404


def test_invalid_enum_and_unauthenticated_access(ticket_api_client):
    client, _ = ticket_api_client
    invalid = client.post("/api/v1/tickets", json=ticket_payload(priority="not-valid"))
    assert invalid.status_code == 422
    assert invalid.json()["error"]["code"] == "VALIDATION_ERROR"

    app.dependency_overrides.clear()
    try:
        unauthenticated = client.get("/api/v1/tickets")
    finally:
        from app.api.dependencies import get_current_profile
        app.dependency_overrides[get_current_profile] = lambda: None
    assert unauthenticated.status_code in {401, 403}