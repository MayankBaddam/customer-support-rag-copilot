from uuid import UUID

from sqlalchemy import Enum, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import ProfileRole, enum_values


class Profile(TimestampMixin, Base):
    __tablename__ = "profiles"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(160), nullable=False)
    role: Mapped[ProfileRole] = mapped_column(
        Enum(ProfileRole, native_enum=False, values_callable=enum_values, validate_strings=True, create_constraint=True),
        nullable=False,
        default=ProfileRole.AGENT,
    )

    assigned_tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="assignee", foreign_keys="Ticket.assigned_to"
    )
    created_tickets: Mapped[list["Ticket"]] = relationship(
        back_populates="creator", foreign_keys="Ticket.created_by"
    )