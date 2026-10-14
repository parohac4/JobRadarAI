from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditEvent


async def log_audit(
    db: AsyncSession,
    *,
    user_id: int | None,
    action: str,
    entity_type: str = "",
    entity_id: str = "",
    payload: dict | None = None,
) -> None:
    db.add(
        AuditEvent(
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            payload=payload or {},
        )
    )
