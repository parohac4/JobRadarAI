from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import JobAvailability, JobInboxStatus, JobSource


class JobListing(Base):
    __tablename__ = "job_listings"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)

    title: Mapped[str] = mapped_column(String(500))
    company: Mapped[str] = mapped_column(String(300), default="")
    location: Mapped[str] = mapped_column(String(300), default="")
    url: Mapped[str] = mapped_column(String(2000), default="")
    source: Mapped[JobSource] = mapped_column(default=JobSource.manual)
    raw_text: Mapped[str] = mapped_column(Text, default="")
    requirements_text: Mapped[str] = mapped_column(Text, default="")

    content_hash: Mapped[str] = mapped_column(String(64), index=True)
    url_hash: Mapped[str] = mapped_column(String(64), index=True, default="")
    duplicate_of_id: Mapped[int | None] = mapped_column(ForeignKey("job_listings.id"), nullable=True)

    availability: Mapped[JobAvailability] = mapped_column(default=JobAvailability.unknown)
    inbox_status: Mapped[JobInboxStatus] = mapped_column(default=JobInboxStatus.active)
    snoozed_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    snooze_note: Mapped[str] = mapped_column(Text, default="")
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    dismissed_note: Mapped[str] = mapped_column(Text, default="")
    posted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    imported_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_checked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user: Mapped["User"] = relationship()
    evaluations: Mapped[list["AiEvaluation"]] = relationship(back_populates="job_listing")
    application: Mapped["Application | None"] = relationship(back_populates="job_listing", uselist=False)
