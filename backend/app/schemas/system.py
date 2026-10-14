from datetime import datetime

from pydantic import BaseModel


class HealthOut(BaseModel):
    status: str
    demo_mode: bool


class SyncRunOut(BaseModel):
    id: int
    source: str
    status: str
    message: str
    started_at: datetime
    finished_at: datetime | None

    model_config = {"from_attributes": True}


class AuditEventOut(BaseModel):
    id: int
    action: str
    entity_type: str
    entity_id: str
    payload: dict
    created_at: datetime

    model_config = {"from_attributes": True}


class DashboardStats(BaseModel):
    total_jobs: int
    open_jobs: int
    applications_active: int
    recommended_count: int
    avg_score: float | None
