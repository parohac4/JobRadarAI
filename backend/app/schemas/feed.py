from datetime import datetime

from pydantic import BaseModel, Field


class FeedSourceCreate(BaseModel):
    title: str = Field("", max_length=200)
    url: str = Field(min_length=8, max_length=2000)
    enabled: bool = True


class FeedSourceUpdate(BaseModel):
    title: str | None = Field(None, max_length=200)
    url: str | None = Field(None, min_length=8, max_length=2000)
    enabled: bool | None = None


class FeedSourceOut(BaseModel):
    id: int
    title: str
    url: str
    enabled: bool
    last_fetched_at: datetime | None
    last_error: str
    created_at: datetime

    model_config = {"from_attributes": True}


class IntegrationsStatus(BaseModel):
    imap_configured: bool
    imap_folder: str
    notify_enabled: bool
    notify_min_score: int
    auto_evaluate_on_import: bool
    ai_provider: str
    worker_enabled: bool
    sync_interval_seconds: int
