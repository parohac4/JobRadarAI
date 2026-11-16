from typing import Literal
from pydantic import BaseModel, Field, HttpUrl


class CustomFeed(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    url: HttpUrl
    enabled: bool = True


class SearchSettings(BaseModel):
    city: str = Field("Strakonice", max_length=150)
    radius_km: int = Field(30, ge=1, le=500)
    keywords: str = Field("", max_length=300)
    ai_enabled: bool = False
    ai_preferences: str = Field("", max_length=4000)
    sources: list[Literal["jobs", "prace", "sitprace", "kariera"]] = Field(
        default_factory=lambda: ["jobs", "prace", "sitprace"], max_length=4)
    custom_feeds: list[CustomFeed] = Field(default_factory=list, max_length=10)
    monitoring_enabled: bool = True
    interval_minutes: Literal[15, 30, 60, 180, 360, 720, 1440] = 30
    include_remote: bool = False
    include_unknown: bool = False
    sort: Literal["match", "distance", "newest", "oldest"] = "newest"
    min_score: int = Field(0, ge=0, le=100)


class InteractionUpdate(BaseModel):
    seen: bool | None = None
    marked: bool | None = None
