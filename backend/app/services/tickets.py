from uuid import UUID, uuid4

from app.core.errors import APIError
from app.models import Conversation, Message, Profile, Ticket
from app.models.enums import SenderType
from app.repositories.tickets import TicketRepository
from app.schemas.tickets import MessageCreate, TicketCreate, TicketUpdate


def _ticket_number() -> str:
    return f"TCK-{uuid4().hex[:12].upper()}"


class TicketService:
    def __init__(self, repository: TicketRepository) -> None:
        self.repository = repository

    def list_tickets(self, **filters):
        return self.repository.list(**filters)

    def create_ticket(self, data: TicketCreate, profile: Profile) -> Ticket:
        if data.assigned_to and not self.repository.profile_exists(data.assigned_to):
            raise APIError("ASSIGNEE_NOT_FOUND", "The assigned profile was not found.", 404)
        ticket = Ticket(
            ticket_number=_ticket_number(),
            subject=data.subject,
            customer_name=data.customer_name,
            customer_email=str(data.customer_email),
            customer_plan=data.customer_plan,
            category=data.category,
            priority=data.priority,
            status=data.status,
            assigned_to=data.assigned_to,
            created_by=profile.id,
        )
        self.repository.add(ticket)
        conversation = self.repository.add_conversation(Conversation(ticket=ticket))
        if data.first_message:
            self._add_message(conversation.id, data.first_message)
        self.repository.commit()
        return self.repository.get_with_details(ticket.id) or ticket

    def get_ticket(self, ticket_id: UUID) -> Ticket:
        ticket = self.repository.get_with_details(ticket_id)
        if ticket is None:
            raise APIError("TICKET_NOT_FOUND", "The ticket was not found.", 404)
        return ticket

    def update_ticket(self, ticket_id: UUID, data: TicketUpdate) -> Ticket:
        ticket = self.repository.get(ticket_id)
        if ticket is None:
            raise APIError("TICKET_NOT_FOUND", "The ticket was not found.", 404)
        if data.assigned_to and not self.repository.profile_exists(data.assigned_to):
            raise APIError("ASSIGNEE_NOT_FOUND", "The assigned profile was not found.", 404)
        for field, value in data.model_dump(exclude_unset=True).items():
            setattr(ticket, field, value)
        self.repository.commit()
        return self.get_ticket(ticket.id)

    def add_message(self, ticket_id: UUID, data: MessageCreate, profile: Profile) -> Message:
        ticket = self.get_ticket(ticket_id)
        conversation = ticket.conversations[0] if ticket.conversations else self.repository.add_conversation(Conversation(ticket=ticket))
        if data.sender_type == SenderType.AGENT:
            data = data.model_copy(update={"sender_name": profile.full_name})
        message = self._add_message(conversation.id, data)
        self.repository.commit()
        self.repository.refresh(message)
        return message

    def _add_message(self, conversation_id: UUID, data: MessageCreate) -> Message:
        return self.repository.add_message(Message(conversation_id=conversation_id, **data.model_dump()))