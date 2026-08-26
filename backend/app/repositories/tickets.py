from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from app.models import Conversation, Message, Profile, Ticket
from app.models.enums import CustomerPlan, TicketCategory, TicketPriority, TicketStatus


class TicketRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list(
        self,
        *,
        page: int,
        page_size: int,
        search: str | None = None,
        status: TicketStatus | None = None,
        priority: TicketPriority | None = None,
        category: TicketCategory | None = None,
        customer_plan: CustomerPlan | None = None,
    ) -> tuple[int, list[Ticket]]:
        query = select(Ticket).order_by(Ticket.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        count_query = select(func.count()).select_from(Ticket)
        conditions = []
        if search:
            term = f"%{search}%"
            conditions.append(or_(Ticket.ticket_number.ilike(term), Ticket.subject.ilike(term), Ticket.customer_name.ilike(term), Ticket.customer_email.ilike(term)))
        if status:
            conditions.append(Ticket.status == status)
        if priority:
            conditions.append(Ticket.priority == priority)
        if category:
            conditions.append(Ticket.category == category)
        if customer_plan:
            conditions.append(Ticket.customer_plan == customer_plan)
        if conditions:
            query = query.where(*conditions)
            count_query = count_query.where(*conditions)
        total = self.session.scalar(count_query) or 0
        return total, list(self.session.scalars(query).all())

    def get_with_details(self, ticket_id: UUID) -> Ticket | None:
        query = (
            select(Ticket)
            .where(Ticket.id == ticket_id)
            .options(selectinload(Ticket.conversations).selectinload(Conversation.messages))
        )
        return self.session.scalar(query)

    def get(self, ticket_id: UUID) -> Ticket | None:
        return self.session.get(Ticket, ticket_id)

    def profile_exists(self, profile_id: UUID) -> bool:
        return self.session.scalar(select(Profile.id).where(Profile.id == profile_id)) is not None

    def add(self, ticket: Ticket) -> Ticket:
        self.session.add(ticket)
        self.session.flush()
        return ticket

    def add_conversation(self, conversation: Conversation) -> Conversation:
        self.session.add(conversation)
        self.session.flush()
        return conversation

    def add_message(self, message: Message) -> Message:
        self.session.add(message)
        self.session.flush()
        return message

    def commit(self) -> None:
        self.session.commit()

    def refresh(self, entity: object) -> None:
        self.session.refresh(entity)