from pydantic import BaseModel, Field


class ProfileUpdate(BaseModel):
    summary: str = ""
    skills: list[str] = Field(default_factory=list)
    experience: list[dict] = Field(default_factory=list)
    education: list[dict] = Field(default_factory=list)
    preferences: dict = Field(default_factory=dict)
    cv_versions: list[dict] = Field(default_factory=list)


class ProfileOut(ProfileUpdate):
    id: int
    user_id: int

    model_config = {"from_attributes": True}
