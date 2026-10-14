import email
import imaplib
import logging
from email.header import decode_header
from email.utils import parsedate_to_datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.import_state import ImportState
from app.models.user import User
from app.schemas.job import JobListingCreate
from app.services import jobs as job_service
from app.services.job_import import parse_job_email

logger = logging.getLogger("jobradar.imap")


def _decode_header(value: str | None) -> str:
    if not value:
        return ""
    parts = decode_header(value)
    out = []
    for chunk, enc in parts:
        if isinstance(chunk, bytes):
            out.append(chunk.decode(enc or "utf-8", errors="replace"))
        else:
            out.append(chunk)
    return "".join(out)


def _fetch_messages(folder: str, last_uid: int, limit: int = 30) -> tuple[list[dict], int]:
    settings = get_settings()
    mail = imaplib.IMAP4_SSL(settings.imap_host, settings.imap_port)
    mail.login(settings.imap_user, settings.imap_password)
    status, _ = mail.select(f'"{folder}"' if " " in folder else folder, readonly=True)
    if status != "OK":
        mail.logout()
        raise RuntimeError(f"IMAP složka '{folder}' není dostupná (zkuste [Gmail]/{folder})")

    criteria = f"(UID {last_uid + 1}:*)" if last_uid else "ALL"
    status, data = mail.uid("search", None, criteria)
    if status != "OK":
        mail.logout()
        return [], last_uid

    uids = [int(x) for x in data[0].split() if x]
    uids = uids[-limit:]
    messages: list[dict] = []
    max_uid = last_uid
    for uid in uids:
        status, msg_data = mail.uid("fetch", str(uid), "(RFC822)")
        if status != "OK" or not msg_data or not msg_data[0]:
            continue
        raw = msg_data[0][1]
        msg = email.message_from_bytes(raw)
        subject = _decode_header(msg.get("Subject"))
        body = ""
        if msg.is_multipart():
            for part in msg.walk():
                if part.get_content_type() == "text/plain":
                    payload = part.get_payload(decode=True)
                    if payload:
                        body += payload.decode(part.get_content_charset() or "utf-8", errors="replace")
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                body = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
        messages.append(
            {
                "uid": uid,
                "subject": subject,
                "body": body,
                "date": parsedate_to_datetime(msg.get("Date")) if msg.get("Date") else None,
            }
        )
        max_uid = max(max_uid, uid)
    mail.logout()
    return messages, max_uid


async def _get_state(db: AsyncSession, user_id: int) -> ImportState:
    result = await db.execute(select(ImportState).where(ImportState.user_id == user_id))
    state = result.scalar_one_or_none()
    if not state:
        state = ImportState(user_id=user_id, imap_uids={})
        db.add(state)
        await db.flush()
    return state


async def sync_imap_for_user(db: AsyncSession, user: User) -> dict:
    settings = get_settings()
    if not settings.imap_configured:
        return {"skipped": True, "reason": "imap_not_configured"}

    folder = settings.imap_folder
    state = await _get_state(db, user.id)
    last_uid = int((state.imap_uids or {}).get(folder, 0))

    try:
        messages, max_uid = _fetch_messages(folder, last_uid)
    except imaplib.IMAP4.error as e:
        logger.exception("IMAP přihlášení selhalo")
        return {"error": f"IMAP: {e}"}
    except Exception as e:
        logger.exception("IMAP sync")
        return {"error": str(e)}

    created = 0
    duplicates = 0
    new_job_ids: list[int] = []
    for item in messages:
        parsed = parse_job_email(item["subject"], item["body"])
        data = JobListingCreate(
            title=parsed["title"],
            company=parsed["company"],
            location=parsed["location"],
            url=parsed["url"],
            raw_text=parsed["raw_text"],
            source=parsed["source"],
        )
        job, dup = await job_service.create_job(db, user.id, data)
        if dup:
            duplicates += 1
        else:
            created += 1
            new_job_ids.append(job.id)
        await db.flush()

    state.imap_uids = {**(state.imap_uids or {}), folder: max_uid}
    await db.commit()
    return {
        "created": created,
        "duplicates": duplicates,
        "fetched": len(messages),
        "last_uid": max_uid,
        "new_job_ids": new_job_ids,
    }
