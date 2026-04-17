from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field


class TicketCreate(BaseModel):
    title: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=10, max_length=4000)


class TicketResponse(BaseModel):
    id: int
    title: str
    description: str
    category: str
    priority: str
    sentiment: str
    status: str
    assignee_id: int | None


class TicketAssignRequest(BaseModel):
    assignee_user_id: int = Field(gt=0)


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
