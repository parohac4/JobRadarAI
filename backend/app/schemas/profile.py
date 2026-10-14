from pydantic import BaseModel, Field


class ProfileUpdate(BaseModel):
    summary: str = Field("", max_length=5000)
    skills: list[str] = Field(default_factory=list, max_length=200)
    experience: list[dict] = Field(default_factory=list, max_length=100)
    education: list[dict] = Field(default_factory=list, max_length=50)
    preferences: dict = Field(default_factory=dict)
    cv_versions: list[dict] = Field(default_factory=list, max_length=20)


class ProfileOut(ProfileUpdate):
    id: int
    user_id: int

    model_config = {"from_attributes": True}
