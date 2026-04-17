from sqlalchemy import Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column
from app.database.base import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80))
    skills: Mapped[str] = mapped_column(String(200), default="")
    current_load: Mapped[int] = mapped_column(Integer, default=0, index=True)

    __table_args__ = (Index("ix_agents_load", "current_load"),)
