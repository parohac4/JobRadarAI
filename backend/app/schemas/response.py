from datetime import datetime

from pydantic import BaseModel, field_validator

from app.services.ai import normalize_cover_letter_content


class GeneratedResponseOut(BaseModel):
    id: int
    job_listing_id: int
    response_type: str
    content: str
    recommended_cv_version: str
    provider: str
    created_at: datetime

    model_config = {"from_attributes": True}

    @field_validator("content", mode="before")
    @classmethod
    def unwrap_cover_letter_json(cls, value: object) -> object:
        if isinstance(value, str):
            return normalize_cover_letter_content(value)
        return value
