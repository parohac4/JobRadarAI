from sqlalchemy import ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ImportState(Base):
    """Per-user stav importů (např. poslední IMAP UID ve složce)."""

    __tablename__ = "import_states"

    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    imap_uids: Mapped[dict] = mapped_column(JSONB, default=dict)
