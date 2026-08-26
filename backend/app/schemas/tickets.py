from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import CustomerPlan, SenderType, TicketCategory, TicketPriority, TicketStatus


class MessageCreate(BaseModel):
    sender_type: SenderType
    sender_name: str = Field(min_length=1, max_length=160)
    content: str = Field(min_length=1)


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    sender_type: SenderType
    sender_name: str
    content: str
    created_at: datetime


class ConversationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    created_at: datetime
    messages: list[MessageResponse]


class TicketCreate(BaseModel):
    subject: str = Field(min_length=1, max_length=240)
    customer_name: str = Field(min_length=1, max_length=160)
    customer_email: EmailStr
    customer_plan: CustomerPlan
    category: TicketCategory
    priority: TicketPriority
    status: TicketStatus = TicketStatus.OPEN
    assigned_to: UUID | None = None
    first_message: MessageCreate | None = None


class TicketUpdate(BaseModel):
    subject: str | None = Field(default=None, min_length=1, max_length=240)
    customer_plan: CustomerPlan | None = None
    category: TicketCategory | None = None
    priority: TicketPriority | None = None
    status: TicketStatus | None = None
    assigned_to: UUID | None = None


class TicketResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    ticket_number: str
    subject: str
    customer_name: str
    customer_email: EmailStr
    customer_plan: CustomerPlan
    category: TicketCategory
    priority: TicketPriority
    status: TicketStatus
    assigned_to: UUID | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime


class TicketDetailResponse(TicketResponse):
    conversations: list[ConversationResponse]


class TicketListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[TicketResponse]