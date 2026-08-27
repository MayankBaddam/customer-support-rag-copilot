from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event
from sqlalchemy.exc import IntegrityError, StatementError
from sqlalchemy.orm import Session

from app.models import (
    Base,
    Conversation,
    CustomerPlan,
    Document,
    DocumentChunk,
    DocumentFileType,
    DocumentStatus,
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


def test_document_required_fields_and_timestamps_are_valid(session):
    profile = Profile(id=uuid4(), full_name="Document Manager", role=ProfileRole.AGENT)
    session.add(profile)
    session.commit()

    document = Document(
        title="Refund policy",
        original_filename="refund-policy.pdf",
        storage_bucket="knowledge-documents",
        storage_path="refund-policy.pdf",
        file_type=DocumentFileType.PDF,
        mime_type="application/pdf",
        file_size_bytes=2048,
        checksum_sha256="abc123",
        uploaded_by=profile.id,
    )
    session.add(document)
    session.commit()

    assert document.version == 1
    assert document.chunk_count == 0
    assert document.status == DocumentStatus.PENDING
    assert document.created_at is not None
    assert document.updated_at is not None


def test_document_enum_validation(session):
    profile = Profile(id=uuid4(), full_name="Document Manager", role=ProfileRole.AGENT)
    session.add(profile)
    session.commit()

    document = Document(
        title="Refund policy",
        original_filename="refund-policy.pdf",
        storage_bucket="knowledge-documents",
        storage_path="refund-policy-invalid.pdf",
        file_type="not-a-file-type",
        mime_type="application/pdf",
        file_size_bytes=2048,
        checksum_sha256="def456",
        uploaded_by=profile.id,
    )
    session.add(document)

    with pytest.raises((StatementError, ValueError)):
        session.commit()


def test_document_storage_path_is_unique(session):
    profile = Profile(id=uuid4(), full_name="Document Manager", role=ProfileRole.AGENT)
    session.add(profile)
    session.commit()

    doc1 = Document(
        title="Policy A",
        original_filename="policy-a.pdf",
        storage_bucket="knowledge-documents",
        storage_path="shared/path/document.pdf",
        file_type=DocumentFileType.PDF,
        mime_type="application/pdf",
        file_size_bytes=1024,
        checksum_sha256="hash-1",
        uploaded_by=profile.id,
    )
    doc2 = Document(
        title="Policy B",
        original_filename="policy-b.pdf",
        storage_bucket="knowledge-documents",
        storage_path="shared/path/document.pdf",
        file_type=DocumentFileType.PDF,
        mime_type="application/pdf",
        file_size_bytes=2048,
        checksum_sha256="hash-2",
        uploaded_by=profile.id,
    )
    session.add_all([doc1, doc2])

    with pytest.raises(IntegrityError):
        session.commit()


def test_document_chunk_indexes_are_unique_per_document(session):
    profile = Profile(id=uuid4(), full_name="Document Manager", role=ProfileRole.AGENT)
    session.add(profile)
    session.commit()

    document = Document(
        title="Refund policy",
        original_filename="refund-policy.pdf",
        storage_bucket="knowledge-documents",
        storage_path="refund-policy.pdf",
        file_type=DocumentFileType.PDF,
        mime_type="application/pdf",
        file_size_bytes=2048,
        checksum_sha256="hash-3",
        uploaded_by=profile.id,
    )
    chunk_a = DocumentChunk(document=document, chunk_index=0, content="first chunk", token_count=15)
    chunk_b = DocumentChunk(document=document, chunk_index=0, content="duplicate chunk", token_count=20)
    session.add_all([document, chunk_a, chunk_b])

    with pytest.raises(IntegrityError):
        session.commit()


def test_document_to_chunk_relationship_and_cascade_deletion(session):
    profile = Profile(id=uuid4(), full_name="Document Manager", role=ProfileRole.AGENT)
    session.add(profile)
    session.commit()

    document = Document(
        title="Support policy",
        original_filename="support-policy.md",
        storage_bucket="knowledge-documents",
        storage_path="support-policy.md",
        file_type=DocumentFileType.MARKDOWN,
        mime_type="text/markdown",
        file_size_bytes=512,
        checksum_sha256="hash-4",
        uploaded_by=profile.id,
    )
    chunk = DocumentChunk(document=document, chunk_index=0, content="Chunk text", token_count=10)
    session.add_all([document, chunk])
    session.commit()

    assert document.chunks == [chunk]
    assert chunk.document is document

    document_id = document.id
    chunk_id = chunk.id
    session.delete(document)
    session.commit()

    assert session.get(Document, document_id) is None
    assert session.get(DocumentChunk, chunk_id) is None