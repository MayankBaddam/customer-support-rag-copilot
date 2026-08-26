from uuid import uuid4

from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session

from app.models import Base, Conversation, Message, Profile, Ticket
from app.seed import seed_database


def test_seed_is_idempotent_and_preserves_relationships():
    engine = create_engine("sqlite://")

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, _):
        dbapi_connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    demo_user_id = uuid4()
    with Session(engine) as session:
        first = seed_database(session, demo_user_id)
        second = seed_database(session, demo_user_id)
        assert first == (20, 60)
        assert second == (0, 0)
        assert session.scalar(select(func.count()).select_from(Profile)) == 1
        assert session.scalar(select(func.count()).select_from(Ticket)) == 20
        assert session.scalar(select(func.count()).select_from(Conversation)) == 20
        assert session.scalar(select(func.count()).select_from(Message)) == 60
        assert all(len(ticket.conversations) == 1 for ticket in session.scalars(select(Ticket)).all())
        assert all(len(conversation.messages) == 3 for conversation in session.scalars(select(Conversation)).all())
    engine.dispose()