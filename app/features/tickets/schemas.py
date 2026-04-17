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
