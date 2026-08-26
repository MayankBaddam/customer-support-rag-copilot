from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session

from app.models import (
    Base,
    Conversation,
    CustomerPlan,
    Message,
    Profile,
    ProfileRole,
    SenderType,
    Ticket,
    TicketCategory,
    TicketPriority,
    TicketStatus,
)


@pytest.fixture
def session():
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    with Session(engine) as database_session:
        yield database_session
    engine.dispose()


def make_ticket(profile_id):
    return Ticket(
        ticket_number="TCK-2001",
        subject="Cannot update plan",
        customer_name="Demo Customer",
        customer_email="customer-2001@example.test",
        customer_plan=CustomerPlan.BASIC,
        category=TicketCategory.SUBSCRIPTION,
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.OPEN,
        created_by=profile_id,
    )


def test_models_create_with_relationships_and_required_fields(session):
    profile = Profile(id=uuid4(), full_name="Demo Agent", role=ProfileRole.AGENT)
    ticket = make_ticket(profile.id)
    conversation = Conversation(ticket=ticket)
    message = Message(
        conversation=conversation,
        sender_type=SenderType.CUSTOMER,
        sender_name="Demo Customer",
        content="Please help.",
    )
    session.add_all([profile, ticket, conversation, message])
    session.commit()

    assert ticket.creator is profile
    assert ticket.conversations == [conversation]
    assert conversation.ticket is ticket
    assert conversation.messages == [message]
    assert message.conversation is conversation
    assert Ticket.__table__.c.created_at.type.timezone is True
    assert Ticket.__table__.c.updated_at.type.timezone is True


def test_enum_values_are_validated(session):
    profile = Profile(id=uuid4(), full_name="Demo Agent", role=ProfileRole.ADMIN)
    session.add(profile)
    session.commit()
    invalid_ticket = make_ticket(profile.id)
    invalid_ticket.status = "not-a-status"
    session.add(invalid_ticket)

    with pytest.raises(StatementError):
        session.commit()


def test_cascade_deletes_conversation_and_messages(session):
    profile = Profile(id=uuid4(), full_name="Demo Agent", role=ProfileRole.AGENT)
    ticket = make_ticket(profile.id)
    conversation = Conversation(ticket=ticket)
    message = Message(
        conversation=conversation,
        sender_type=SenderType.AGENT,
        sender_name="Demo Agent",
        content="We are reviewing this.",
    )
    session.add_all([profile, ticket, conversation, message])
    session.commit()
    conversation_id, message_id = conversation.id, message.id

    session.delete(ticket)
    session.commit()

    assert session.get(Conversation, conversation_id) is None
    assert session.get(Message, message_id) is None


def test_ticket_number_is_unique(session):
    profile = Profile(id=uuid4(), full_name="Demo Agent", role=ProfileRole.AGENT)
    session.add(profile)
    session.commit()
    session.add_all([make_ticket(profile.id), make_ticket(profile.id)])

    with pytest.raises(IntegrityError):
        session.commit()


def test_required_fields_are_enforced(session):
    session.add(Profile(id=uuid4()))

    with pytest.raises(IntegrityError):
        session.commit()