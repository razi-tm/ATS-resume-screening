from __future__ import annotations

import enum
from datetime import datetime
from uuid import uuid4

from sqlalchemy import DateTime, Enum, Float, ForeignKey, Index, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import Uuid

from app.core.database import Base


class Role(str, enum.Enum):
    admin = "admin"
    recruiter = "recruiter"
    viewer = "viewer"


class ScreeningStatus(str, enum.Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class Organization(TimestampMixin, Base):
    __tablename__ = "organizations"
    id: Mapped[Uuid] = mapped_column(Uuid, primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    users: Mapped[list["User"]] = relationship(back_populates="organization")


class User(TimestampMixin, Base):
    __tablename__ = "users"
    id: Mapped[Uuid] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[Uuid] = mapped_column(ForeignKey("organizations.id"), index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[Role] = mapped_column(Enum(Role), default=Role.recruiter)
    organization: Mapped[Organization] = relationship(back_populates="users")


class Job(TimestampMixin, Base):
    __tablename__ = "jobs"
    id: Mapped[Uuid] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[Uuid] = mapped_column(ForeignKey("organizations.id"), index=True)
    title: Mapped[str] = mapped_column(String(255), index=True)
    description: Mapped[str] = mapped_column(Text)
    required_skills: Mapped[list[str]] = mapped_column(JSON, default=list)
    min_years_experience: Mapped[float] = mapped_column(Float, default=0)


class Resume(TimestampMixin, Base):
    __tablename__ = "resumes"
    id: Mapped[Uuid] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[Uuid] = mapped_column(ForeignKey("organizations.id"), index=True)
    candidate_name: Mapped[str | None] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), index=True)
    file_name: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    text: Mapped[str] = mapped_column(Text)
    parsed_data: Mapped[dict] = mapped_column(JSON, default=dict)


class Screening(TimestampMixin, Base):
    __tablename__ = "screenings"
    id: Mapped[Uuid] = mapped_column(Uuid, primary_key=True, default=uuid4)
    organization_id: Mapped[Uuid] = mapped_column(ForeignKey("organizations.id"), index=True)
    job_id: Mapped[Uuid] = mapped_column(ForeignKey("jobs.id"), index=True)
    status: Mapped[ScreeningStatus] = mapped_column(Enum(ScreeningStatus), default=ScreeningStatus.queued, index=True)
    weights: Mapped[dict] = mapped_column(JSON, default=dict)


class ScreeningResult(TimestampMixin, Base):
    __tablename__ = "screening_results"
    id: Mapped[Uuid] = mapped_column(Uuid, primary_key=True, default=uuid4)
    screening_id: Mapped[Uuid] = mapped_column(ForeignKey("screenings.id"), index=True)
    resume_id: Mapped[Uuid] = mapped_column(ForeignKey("resumes.id"), index=True)
    rank: Mapped[int] = mapped_column(Integer)
    final_score: Mapped[float] = mapped_column(Float, index=True)
    semantic_score: Mapped[float] = mapped_column(Float)
    keyword_score: Mapped[float] = mapped_column(Float)
    skills_score: Mapped[float] = mapped_column(Float)
    explanation: Mapped[list[str]] = mapped_column(JSON, default=list)

Index("ix_results_screening_rank", ScreeningResult.screening_id, ScreeningResult.rank)
