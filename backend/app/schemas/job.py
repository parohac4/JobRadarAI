from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import JobAvailability, JobInboxStatus, JobSource


class JobListingCreate(BaseModel):
    model_config = {"str_strip_whitespace": True}

    title: str = Field(min_length=1, max_length=500)
    company: str = Field("", max_length=300)
    location: str = Field("", max_length=300)
    url: str = Field("", max_length=2000)
    raw_text: str = Field("", max_length=50000)
    requirements_text: str = Field("", max_length=20000)
    source: JobSource = JobSource.manual


class JobImportUrl(BaseModel):
    url: str = Field(min_length=8, max_length=2000)


class JobImportEmail(BaseModel):
    email_body: str = Field(min_length=20, max_length=50000)
    subject: str = Field("", max_length=500)


class JobSnoozeIn(BaseModel):
    note: str = Field(min_length=1, max_length=2000)
    days: int = Field(default=7, ge=1, le=365)


class JobDismissIn(BaseModel):
    note: str = Field(min_length=1, max_length=2000)


class JobListingOut(BaseModel):
    id: int
    title: str
    company: str
    location: str
    url: str
    source: JobSource
    raw_text: str
    availability: JobAvailability
    duplicate_of_id: int | None
    imported_at: datetime
    latest_score: int | None = None
    distance_km: float | None = None
    location_remote: bool = False
    location_unknown: bool = False
    inbox_status: JobInboxStatus
    snoozed_until: datetime | None = None
    snooze_note: str = ""
    dismissed_at: datetime | None = None
    dismissed_note: str = ""

    model_config = {"from_attributes": True}


class JobListingDetail(JobListingOut):
    requirements_text: str
    evaluations_count: int = 0
