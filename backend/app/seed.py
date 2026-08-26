import json
from pathlib import Path
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.database.session import get_database_engine
from app.models import Conversation, CustomerPlan, Message, Profile, ProfileRole, SenderType, Ticket, TicketCategory, TicketPriority, TicketStatus

DATA_PATH = Path(__file__).resolve().parents[2] / "evaluation" / "datasets" / "tickets.json"
STATUS_MAP = {"open": TicketStatus.OPEN, "in_progress": TicketStatus.IN_PROGRESS, "pending": TicketStatus.WAITING, "waiting": TicketStatus.WAITING, "closed": TicketStatus.RESOLVED, "resolved": TicketStatus.RESOLVED}
PRIORITY_MAP = {"low": TicketPriority.LOW, "medium": TicketPriority.MEDIUM, "high": TicketPriority.HIGH, "urgent": TicketPriority.URGENT, "critical": TicketPriority.URGENT}
CATEGORY_MAP = {"Billing": TicketCategory.BILLING, "Account access": TicketCategory.ACCOUNT_ACCESS, "Subscription": TicketCategory.SUBSCRIPTION, "Integrations": TicketCategory.INTEGRATION, "Security": TicketCategory.SECURITY, "Technical troubleshooting": TicketCategory.TECHNICAL}
PLAN_SEQUENCE = (CustomerPlan.FREE, CustomerPlan.BASIC, CustomerPlan.PRO)
CUSTOMER_NAMES = ("Avery Morgan", "Jordan Ellis", "Casey Rowan", "Riley Brooks", "Morgan Taylor")


def load_ticket_seed_data() -> list[dict]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def seed_database(session: Session, demo_user_id: UUID) -> tuple[int, int]:
    profile = session.get(Profile, demo_user_id)
    if profile is None:
        profile = Profile(id=demo_user_id, full_name="CloudDesk Demo Agent", role=ProfileRole.AGENT)
        session.add(profile)
        session.flush()

    created_tickets = 0
    created_messages = 0
    for index, item in enumerate(load_ticket_seed_data()):
        ticket_number = item["id"]
        ticket = session.scalar(select(Ticket).where(Ticket.ticket_number == ticket_number))
        if ticket is not None:
            continue
        customer_name = CUSTOMER_NAMES[index % len(CUSTOMER_NAMES)]
        ticket = Ticket(
            ticket_number=ticket_number,
            subject=item["subject"],
            customer_name=customer_name,
            customer_email=f"{ticket_number.lower()}@example.com",
            customer_plan=PLAN_SEQUENCE[index % len(PLAN_SEQUENCE)],
            category=CATEGORY_MAP[item["category"]],
            priority=PRIORITY_MAP[item["priority"]],
            status=STATUS_MAP[item["status"]],
            created_by=demo_user_id,
        )
        ticket.conversations.append(
            Conversation(messages=[
                Message(sender_type=SenderType.CUSTOMER, sender_name=customer_name, content=item["description"]),
                Message(sender_type=SenderType.AGENT, sender_name=profile.full_name, content="Thanks for contacting CloudDesk support. We are reviewing the request."),
                Message(sender_type=SenderType.SYSTEM, sender_name="CloudDesk system", content="Demo seed conversation created for local support workflow testing."),
            ])
        )
        session.add(ticket)
        created_tickets += 1
        created_messages += 3
    session.commit()
    return created_tickets, created_messages


def main() -> None:
    raw_user_id = get_settings().seed_demo_user_id
    if not raw_user_id:
        raise RuntimeError("SEED_DEMO_USER_ID must be set to an existing Supabase Auth user UUID.")
    try:
        demo_user_id = UUID(raw_user_id)
    except ValueError as error:
        raise RuntimeError("SEED_DEMO_USER_ID must be a valid UUID.") from error
    with Session(get_database_engine()) as session:
        tickets, messages = seed_database(session, demo_user_id)
    print(f"Seed complete: {tickets} tickets and {messages} messages created.")


if __name__ == "__main__":
    main()