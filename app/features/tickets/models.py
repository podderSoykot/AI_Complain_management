from sqlalchemy import Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base


class Ticket(Base):
    __tablename__ = "tickets"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(String(160), index=True)
    description: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(50), index=True, default="unclassified")
    priority: Mapped[str] = mapped_column(String(30), index=True, default="medium")
    sentiment: Mapped[str] = mapped_column(String(30), default="neutral")
    status: Mapped[str] = mapped_column(String(30), index=True, default="open")
    assignee_id: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    __table_args__ = (
        Index("ix_tickets_status_priority", "status", "priority"),
        Index("ix_tickets_category_status", "category", "status"),
    )
