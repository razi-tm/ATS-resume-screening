from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


class SignupRequest(BaseModel):
    organization_name: str = Field(min_length=2, max_length=200)
    email: EmailStr
    password: str = Field(min_length=10)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


class JobCreate(BaseModel):
    title: str
    description: str
    required_skills: list[str] = []
    min_years_experience: float = 0


class JobRead(JobCreate):
    id: UUID


class ScreeningCreate(BaseModel):
    job_id: UUID
    resume_ids: list[UUID]
    weights: dict[str, float] = {}


class ScreeningRead(BaseModel):
    id: UUID
    status: str
