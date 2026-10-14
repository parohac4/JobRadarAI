from datetime import datetime

from pydantic import BaseModel


class EvaluationOut(BaseModel):
    id: int
    job_listing_id: int
    score: int
    summary: str
    reasons: list
    required_skills: list
    preferred_skills: list
    pros: list
    cons: list
    risks: list
    provider: str
    created_at: datetime

    model_config = {"from_attributes": True}
