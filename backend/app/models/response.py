from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class GeneratedResponse(Base):
    __tablename__ = "generated_responses"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_listing_id: Mapped[int] = mapped_column(ForeignKey("job_listings.id", ondelete="CASCADE"), index=True)
    response_type: Mapped[str] = mapped_column(Text, default="cover_letter")
    content: Mapped[str] = mapped_column(Text)
    recommended_cv_version: Mapped[str] = mapped_column(Text, default="")
    provider: Mapped[str] = mapped_column(Text, default="mock")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
