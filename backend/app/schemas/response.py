from datetime import datetime

from pydantic import BaseModel


class GeneratedResponseOut(BaseModel):
    id: int
    job_listing_id: int
    response_type: str
    content: str
    recommended_cv_version: str
    provider: str
    created_at: datetime

    model_config = {"from_attributes": True}
