"""Add profiles, tickets, conversations, and messages.

Revision ID: 20260826_add_support_schema
Revises: 20260826_enable_pgvector
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "20260826_add_support_schema"
down_revision = "20260826_enable_pgvector"
branch_labels = None
depends_on = None


profile_role = postgresql.ENUM("agent", "admin", name="profile_role", create_type=False)
customer_plan = postgresql.ENUM("free", "basic", "pro", name="customer_plan", create_type=False)
ticket_category = postgresql.ENUM(
    "billing", "account_access", "subscription", "integration", "security", "technical",
    name="ticket_category", create_type=False,
)
ticket_priority = postgresql.ENUM("low", "medium", "high", "urgent", name="ticket_priority", create_type=False)
ticket_status = postgresql.ENUM("open", "in_progress", "waiting", "resolved", name="ticket_status", create_type=False)
sender_type = postgresql.ENUM("customer", "agent", "system", name="sender_type", create_type=False)


def upgrade() -> None:
    bind = op.get_bind()
    for enum_type in (profile_role, customer_plan, ticket_category, ticket_priority, ticket_status, sender_type):
        enum_type.create(bind, checkfirst=True)

    op.create_table(
        "profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("full_name", sa.String(length=160), nullable=False),
        sa.Column("role", profile_role, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_table(
        "tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ticket_number", sa.String(length=32), nullable=False),
        sa.Column("subject", sa.String(length=240), nullable=False),
        sa.Column("customer_name", sa.String(length=160), nullable=False),
        sa.Column("customer_email", sa.String(length=320), nullable=False),
        sa.Column("customer_plan", customer_plan, nullable=False),
        sa.Column("category", ticket_category, nullable=False),
        sa.Column("priority", ticket_priority, nullable=False),
        sa.Column("status", ticket_status, nullable=False),
        sa.Column("assigned_to", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id"), nullable=True),
        sa.Column("created_by", postgresql.UUID(as_uuid=True), sa.ForeignKey("profiles.id"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.UniqueConstraint("ticket_number"),
    )
    op.create_index("ix_tickets_status", "tickets", ["status"])
    op.create_index("ix_tickets_priority", "tickets", ["priority"])
    op.create_index("ix_tickets_category", "tickets", ["category"])
    op.create_index("ix_tickets_assigned_to", "tickets", ["assigned_to"])
    op.create_index("ix_tickets_created_at", "tickets", ["created_at"])
    op.create_table(
        "conversations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("ticket_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("tickets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_conversations_ticket_id", "conversations", ["ticket_id"])
    op.create_table(
        "messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("conversation_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sender_type", sender_type, nullable=False),
        sa.Column("sender_name", sa.String(length=160), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])


def downgrade() -> None:
    op.drop_index("ix_messages_conversation_id", table_name="messages")
    op.drop_table("messages")
    op.drop_index("ix_conversations_ticket_id", table_name="conversations")
    op.drop_table("conversations")
    for index_name in ("ix_tickets_created_at", "ix_tickets_assigned_to", "ix_tickets_category", "ix_tickets_priority", "ix_tickets_status"):
        op.drop_index(index_name, table_name="tickets")
    op.drop_table("tickets")
    op.drop_table("profiles")
    bind = op.get_bind()
    for enum_type in (sender_type, ticket_status, ticket_priority, ticket_category, customer_plan, profile_role):
        enum_type.drop(bind, checkfirst=True)