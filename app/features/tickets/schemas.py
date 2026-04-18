from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class TicketCreate(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=10, max_length=4000)


class TicketAttachmentPublic(BaseModel):
    id: int
    original_filename: str
    content_type: str
    size_bytes: int
    created_at: datetime


class TicketResponse(BaseModel):
    id: int
    title: str
    description: str
    category: str
    priority: str
    sentiment: str
    status: str
    assignee_id: int | None
    reporter_id: int | None = None
    attachment_count: int = 0
    attachments: list[TicketAttachmentPublic] = Field(default_factory=list)
    # Populated on admin ticket list (join) so resolved tickets show who handled them.
    assignee_full_name: str | None = None
    assignee_department: str | None = None


def ticket_response_from_row(row, *, attachments: list[TicketAttachmentPublic] | None = None) -> TicketResponse:
    ac = getattr(row, "attachment_count", None)
    if ac is None:
        ac = len(attachments or [])
    return TicketResponse(
        id=row.id,
        title=row.title,
        description=row.description,
        category=row.category,
        priority=row.priority,
        sentiment=row.sentiment,
        status=row.status,
        assignee_id=row.assignee_id,
        reporter_id=getattr(row, "reporter_id", None),
        attachment_count=int(ac),
        attachments=list(attachments or []),
        assignee_full_name=getattr(row, "assignee_full_name", None),
        assignee_department=getattr(row, "assignee_department", None),
    )


class TicketAssignRequest(BaseModel):
    assignee_user_id: int = Field(gt=0)


class TicketRoutingCandidate(BaseModel):
    user_id: int
    full_name: str
    email: str
    role: str
    department: str
    department_match_score: int = Field(ge=0)
    active_tickets: int = Field(ge=0)
    rationale: str


class TicketRoutingSuggestionResponse(BaseModel):
    """NLP-style routing help: match complaint theme to employee departments + workload."""

    ticket_id: int
    nlp_category: str
    admin_guidance: str
    candidates: list[TicketRoutingCandidate]
    recommended_user_id: int | None = None


TicketWorkStatus = Literal["in_review", "in_progress", "resolved"]
ConversationType = Literal["note", "question", "document_request", "user_reply", "resolution_note"]


class TicketStatusUpdateRequest(BaseModel):
    status: TicketWorkStatus


class TicketConversationCreate(BaseModel):
    message: str = Field(min_length=2, max_length=4000)
    message_type: ConversationType = "note"


class TicketConversationResponse(BaseModel):
    id: int
    ticket_id: int
    sender_user_id: int
    sender_role: str
    message_type: str
    message: str
    created_at: datetime
