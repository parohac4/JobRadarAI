from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class NotificationSent(Base):
    """Zabrání opakovaným upozorněním na stejnou nabídku."""

    __tablename__ = "notifications_sent"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    job_listing_id: Mapped[int] = mapped_column(ForeignKey("job_listings.id", ondelete="CASCADE"), index=True)
    channel: Mapped[str] = mapped_column(String(32))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
