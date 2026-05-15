from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.security import create_access_token, hash_password
from app.models.domain import Job, Organization, Role, User
from app.schemas.api import JobCreate, JobRead, ScreeningCreate, ScreeningRead, SignupRequest, TokenResponse
from app.services.screening import ScreeningService

router = APIRouter(prefix="/api/v1")


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/metrics")
async def metrics() -> str:
    return "ats_api_up 1\n"


@router.post("/auth/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupRequest, session: AsyncSession = Depends(get_session)) -> TokenResponse:
    existing = await session.scalar(select(User).where(User.email == payload.email))
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")
    org = Organization(name=payload.organization_name)
    session.add(org)
    await session.flush()
    user = User(organization_id=org.id, email=payload.email, password_hash=hash_password(payload.password), role=Role.admin)
    session.add(user)
    await session.commit()
    return TokenResponse(access_token=create_access_token(user.id, user.role.value))


@router.post("/jobs", response_model=JobRead, status_code=status.HTTP_201_CREATED)
async def create_job(payload: JobCreate, session: AsyncSession = Depends(get_session)) -> JobRead:
    # Demo tenant until auth dependency is wired for every route.
    org = await session.scalar(select(Organization).limit(1))
    if org is None:
        org = Organization(name="Demo Organization")
        session.add(org)
        await session.flush()
    job = Job(organization_id=org.id, **payload.model_dump())
    session.add(job)
    await session.commit()
    await session.refresh(job)
    return JobRead(id=job.id, title=job.title, description=job.description, required_skills=job.required_skills, min_years_experience=job.min_years_experience)


@router.post("/screenings/preview")
async def preview_screening(job_description: str, files: list[UploadFile] = File(...)) -> list[dict]:
    allowed = {"application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document", "text/plain"}
    resumes: dict[str, str] = {}
    for file in files:
        if file.content_type not in allowed:
            raise HTTPException(status_code=415, detail=f"Unsupported MIME type: {file.content_type}")
        payload = await file.read()
        if len(payload) > 15 * 1024 * 1024:
            raise HTTPException(status_code=413, detail="File too large")
        resumes[file.filename or "resume.txt"] = payload.decode("utf-8", errors="ignore") if file.content_type == "text/plain" else ""
    return ScreeningService().screen_texts(job_description, resumes)


@router.post("/screenings", response_model=ScreeningRead, status_code=status.HTTP_202_ACCEPTED)
async def create_screening(payload: ScreeningCreate) -> ScreeningRead:
    return ScreeningRead(id=payload.job_id, status="queued")
