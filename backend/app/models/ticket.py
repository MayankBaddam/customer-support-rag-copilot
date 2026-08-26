from uuid import UUID, uuid4

from sqlalchemy import Enum, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import CustomerPlan, TicketCategory, TicketPriority, TicketStatus, enum_values


class Ticket(TimestampMixin, Base):
    __tablename__ = "tickets"
    __table_args__ = (
        Index("ix_tickets_status", "status"),
        Index("ix_tickets_priority", "priority"),
        Index("ix_tickets_category", "category"),
        Index("ix_tickets_assigned_to", "assigned_to"),
        Index("ix_tickets_created_at", "created_at"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    ticket_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False, index=True)
    subject: Mapped[str] = mapped_column(String(240), nullable=False)
    customer_name: Mapped[str] = mapped_column(String(160), nullable=False)
    customer_email: Mapped[str] = mapped_column(String(320), nullable=False)
    customer_plan: Mapped[CustomerPlan] = mapped_column(
        Enum(CustomerPlan, native_enum=False, values_callable=enum_values, validate_strings=True, create_constraint=True),
        nullable=False,
    )
    category: Mapped[TicketCategory] = mapped_column(
        Enum(TicketCategory, native_enum=False, values_callable=enum_values, validate_strings=True, create_constraint=True),
        nullable=False,
    )
    priority: Mapped[TicketPriority] = mapped_column(
        Enum(TicketPriority, native_enum=False, values_callable=enum_values, validate_strings=True, create_constraint=True),
        nullable=False,
    )
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus, native_enum=False, values_callable=enum_values, validate_strings=True, create_constraint=True),
        nullable=False,
    )
    assigned_to: Mapped[UUID | None] = mapped_column(ForeignKey("profiles.id"), nullable=True)
    created_by: Mapped[UUID] = mapped_column(ForeignKey("profiles.id"), nullable=False)

    assignee: Mapped["Profile | None"] = relationship(
        back_populates="assigned_tickets", foreign_keys=[assigned_to]
    )
    creator: Mapped["Profile"] = relationship(back_populates="created_tickets", foreign_keys=[created_by])
    conversations: Mapped[list["Conversation"]] = relationship(
        back_populates="ticket", cascade="all, delete-orphan", passive_deletes=True
    )