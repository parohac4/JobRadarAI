from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class AiEvaluation(Base):
    __tablename__ = "ai_evaluations"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_listing_id: Mapped[int] = mapped_column(ForeignKey("job_listings.id", ondelete="CASCADE"), index=True)

    score: Mapped[int] = mapped_column(Integer)
    summary: Mapped[str] = mapped_column(Text, default="")
    reasons: Mapped[list] = mapped_column(JSONB, default=list)
    required_skills: Mapped[list] = mapped_column(JSONB, default=list)
    preferred_skills: Mapped[list] = mapped_column(JSONB, default=list)
    pros: Mapped[list] = mapped_column(JSONB, default=list)
    cons: Mapped[list] = mapped_column(JSONB, default=list)
    risks: Mapped[list] = mapped_column(JSONB, default=list)
    provider: Mapped[str] = mapped_column(Text, default="mock")

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    job_listing: Mapped["JobListing"] = relationship(back_populates="evaluations")
