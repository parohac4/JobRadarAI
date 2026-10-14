from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import ApplicationStatus


class ApplicationStatusUpdate(BaseModel):
    status: ApplicationStatus
    note: str = Field("", max_length=2000)


class ApplicationNoteCreate(BaseModel):
    body: str = Field(min_length=1, max_length=10000)


class ApplicationNoteOut(BaseModel):
    id: int
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ApplicationOut(BaseModel):
    id: int
    job_listing_id: int
    status: ApplicationStatus
    updated_at: datetime
    job_title: str | None = None
    company: str | None = None

    model_config = {"from_attributes": True}


class ApplicationHistoryOut(BaseModel):
    id: int
    from_status: ApplicationStatus | None
    to_status: ApplicationStatus
    note: str
    created_at: datetime

    model_config = {"from_attributes": True}
