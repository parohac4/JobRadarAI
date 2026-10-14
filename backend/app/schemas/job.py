from datetime import datetime

from pydantic import BaseModel, Field

from app.models.enums import JobAvailability, JobSource


class JobListingCreate(BaseModel):
    title: str = Field(min_length=1, max_length=500)
    company: str = ""
    location: str = ""
    url: str = ""
    raw_text: str = ""
    requirements_text: str = ""
    source: JobSource = JobSource.manual


class JobImportUrl(BaseModel):
    url: str = Field(min_length=8, max_length=2000)


class JobImportEmail(BaseModel):
    email_body: str = Field(min_length=20)
    subject: str = ""


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

    model_config = {"from_attributes": True}


class JobListingDetail(JobListingOut):
    requirements_text: str
    evaluations_count: int = 0
