import logging
import smtplib
from email.message import EmailMessage

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.job import JobListing
from app.models.notification_sent import NotificationSent
from app.models.user import User

logger = logging.getLogger("jobradar.notify")


async def _already_sent(db: AsyncSession, user_id: int, job_id: int, channel: str) -> bool:
    result = await db.execute(
        select(NotificationSent.id).where(
            NotificationSent.user_id == user_id,
            NotificationSent.job_listing_id == job_id,
            NotificationSent.channel == channel,
        )
    )
    return result.first() is not None


async def _mark_sent(db: AsyncSession, user_id: int, job_id: int, channel: str) -> None:
    db.add(NotificationSent(user_id=user_id, job_listing_id=job_id, channel=channel))


def _send_email(subject: str, body: str) -> None:
    settings = get_settings()
    if not settings.notify_email_to or not settings.smtp_host:
        return
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from or settings.smtp_user or settings.notify_email_to
    msg["To"] = settings.notify_email_to
    msg.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=30) as smtp:
        smtp.starttls()
        if settings.smtp_user and settings.smtp_password:
            smtp.login(settings.smtp_user, settings.smtp_password)
        smtp.send_message(msg)


async def _send_telegram(text: str) -> None:
    settings = get_settings()
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return
    url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
    async with httpx.AsyncClient(timeout=20.0) as client:
        await client.post(url, json={"chat_id": settings.telegram_chat_id, "text": text[:4000]})


async def notify_job_match(
    db: AsyncSession,
    user: User,
    job: JobListing,
    score: int,
) -> dict:
    settings = get_settings()
    if not settings.notify_enabled or score < settings.notify_min_score:
        return {"sent": []}

    sent: list[str] = []
    subject = f"JobRadar: {job.title} ({score})"
    body = (
        f"Nová doporučená nabídka (skóre {score}/100)\n\n"
        f"{job.title}\n{job.company} · {job.location or 'lokalita neuvedena'}\n"
        f"{job.url or '(bez URL)'}\n"
    )

    if settings.notify_email_to and settings.smtp_host:
        if not await _already_sent(db, user.id, job.id, "email"):
            try:
                _send_email(subject, body)
                await _mark_sent(db, user.id, job.id, "email")
                sent.append("email")
            except Exception:
                logger.exception("E-mail notifikace selhala")

    if settings.telegram_bot_token:
        if not await _already_sent(db, user.id, job.id, "telegram"):
            try:
                await _send_telegram(f"*{job.title}* ({score})\n{job.company}\n{job.url or ''}")
                await _mark_sent(db, user.id, job.id, "telegram")
                sent.append("telegram")
            except Exception:
                logger.exception("Telegram notifikace selhala")

    if sent:
        await db.commit()
    return {"sent": sent}
