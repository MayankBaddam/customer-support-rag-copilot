from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_profile
from app.database.session import get_db
from app.models import Profile
from app.models.enums import CustomerPlan, TicketCategory, TicketPriority, TicketStatus
from app.repositories.tickets import TicketRepository
from app.schemas.tickets import MessageCreate, MessageResponse, TicketCreate, TicketDetailResponse, TicketListResponse, TicketResponse, TicketUpdate
from app.services.tickets import TicketService

router = APIRouter(prefix="/tickets", tags=["tickets"])


def service(session: Annotated[Session, Depends(get_db)]) -> TicketService:
    return TicketService(TicketRepository(session))


@router.get("", response_model=TicketListResponse)
def list_tickets(
    ticket_service: Annotated[TicketService, Depends(service)],
    _: Annotated[Profile, Depends(get_current_profile)],
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: str | None = None,
    status_filter: TicketStatus | None = Query(None, alias="status"),
    priority: TicketPriority | None = None,
    category: TicketCategory | None = None,
    customer_plan: CustomerPlan | None = Query(None, alias="plan"),
) -> TicketListResponse:
    total, items = ticket_service.list_tickets(page=page, page_size=page_size, search=search, status=status_filter, priority=priority, category=category, customer_plan=customer_plan)
    return TicketListResponse(total=total, page=page, page_size=page_size, items=items)


@router.post("", response_model=TicketDetailResponse, status_code=status.HTTP_201_CREATED)
def create_ticket(data: TicketCreate, ticket_service: Annotated[TicketService, Depends(service)], profile: Annotated[Profile, Depends(get_current_profile)]) -> TicketDetailResponse:
    return ticket_service.create_ticket(data, profile)


@router.get("/{ticket_id}", response_model=TicketDetailResponse)
def get_ticket(ticket_id: UUID, ticket_service: Annotated[TicketService, Depends(service)], _: Annotated[Profile, Depends(get_current_profile)]) -> TicketDetailResponse:
    return ticket_service.get_ticket(ticket_id)


@router.patch("/{ticket_id}", response_model=TicketDetailResponse)
def update_ticket(ticket_id: UUID, data: TicketUpdate, ticket_service: Annotated[TicketService, Depends(service)], _: Annotated[Profile, Depends(get_current_profile)]) -> TicketDetailResponse:
    return ticket_service.update_ticket(ticket_id, data)


@router.post("/{ticket_id}/messages", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def add_message(ticket_id: UUID, data: MessageCreate, ticket_service: Annotated[TicketService, Depends(service)], profile: Annotated[Profile, Depends(get_current_profile)]) -> MessageResponse:
    return ticket_service.add_message(ticket_id, data, profile)