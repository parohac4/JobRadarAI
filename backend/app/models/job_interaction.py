from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, false
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class JobInteraction(Base):
    """User state kept independently of imports and AI evaluations."""

    __tablename__ = "job_interactions"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("job_listings.id", ondelete="CASCADE"), primary_key=True)
    seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    marked: Mapped[bool] = mapped_column(Boolean, default=False, server_default=false())
    marked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
