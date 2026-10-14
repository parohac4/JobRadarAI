import enum


class JobSource(str, enum.Enum):
    manual = "manual"
    url = "url"
    email = "email"
    rss = "rss"
    api = "api"


class JobAvailability(str, enum.Enum):
    open = "open"
    closed = "closed"
    unknown = "unknown"


class ApplicationStatus(str, enum.Enum):
    new_offer = "new_offer"
    recommended = "recommended"
    response_ready = "response_ready"
    sent = "sent"
    waiting = "waiting"
    interview = "interview"
    rejected = "rejected"
    accepted = "accepted"
    archived = "archived"
