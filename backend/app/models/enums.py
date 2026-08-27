from enum import StrEnum


def enum_values(enum_type: type[StrEnum]) -> list[str]:
    return [member.value for member in enum_type]


class ProfileRole(StrEnum):
    AGENT = "agent"
    ADMIN = "admin"


class CustomerPlan(StrEnum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"


class TicketCategory(StrEnum):
    BILLING = "billing"
    ACCOUNT_ACCESS = "account_access"
    SUBSCRIPTION = "subscription"
    INTEGRATION = "integration"
    SECURITY = "security"
    TECHNICAL = "technical"


class TicketPriority(StrEnum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"


class TicketStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING = "waiting"
    RESOLVED = "resolved"


class SenderType(StrEnum):
    CUSTOMER = "customer"
    AGENT = "agent"
    SYSTEM = "system"


class DocumentFileType(StrEnum):
    PDF = "pdf"
    MARKDOWN = "markdown"
    TEXT = "text"


class DocumentStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    ARCHIVED = "archived"