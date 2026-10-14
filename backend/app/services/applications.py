from datetime import datetime, timedelta, timezone

from sqlalchemy import and_, or_

from app.models.application import Application


def application_inbox_clause(inbox: str):
    now = datetime.now(timezone.utc)
    if inbox == "snoozed":
        return and_(Application.next_action_at.isnot(None), Application.next_action_at > now)
    return or_(Application.next_action_at.is_(None), Application.next_action_at <= now)


def snooze_application(app: Application, *, note: str, days: int) -> None:
    until = datetime.now(timezone.utc) + timedelta(days=days)
    app.next_action_at = until
    app.snooze_note = note.strip()


def clear_application_snooze(app: Application) -> None:
    app.next_action_at = None
    app.snooze_note = ""
