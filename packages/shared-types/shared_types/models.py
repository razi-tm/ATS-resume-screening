from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4


@dataclass(slots=True)
class ContactInfo:
    name: str | None = None
    email: str | None = None
    phone: str | None = None
    location: str | None = None


@dataclass(slots=True)
class ResumeProfile:
    id: UUID = field(default_factory=uuid4)
    file_name: str = ""
    raw_text: str = ""
    contact: ContactInfo = field(default_factory=ContactInfo)
    skills: list[str] = field(default_factory=list)
    education: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    projects: list[str] = field(default_factory=list)
    job_titles: list[str] = field(default_factory=list)
    languages: list[str] = field(default_factory=list)
    years_experience: float = 0.0
    created_at: datetime = field(default_factory=datetime.utcnow)


@dataclass(slots=True)
class JobDescription:
    title: str = ""
    description: str = ""
    required_skills: list[str] = field(default_factory=list)
    preferred_skills: list[str] = field(default_factory=list)
    min_years_experience: float = 0.0
    education_requirements: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ScreeningWeights:
    semantic: float = 0.45
    keyword: float = 0.25
    skills: float = 0.20
    experience: float = 0.10

    def normalized(self) -> "ScreeningWeights":
        total = self.semantic + self.keyword + self.skills + self.experience
        if total <= 0:
            return ScreeningWeights()
        return ScreeningWeights(
            semantic=self.semantic / total,
            keyword=self.keyword / total,
            skills=self.skills / total,
            experience=self.experience / total,
        )


@dataclass(slots=True)
class CandidateScore:
    resume_id: UUID
    candidate_name: str
    file_name: str
    final_score: float
    semantic_score: float
    keyword_score: float
    skills_score: float
    experience_score: float
    matched_skills: list[str]
    missing_skills: list[str]
    explanations: list[str]
    extracted_data: dict[str, Any]
