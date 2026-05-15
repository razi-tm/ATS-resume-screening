from __future__ import annotations

import io
import logging
import re
from dataclasses import dataclass
from pathlib import Path

from shared_types import ContactInfo, ResumeProfile

LOGGER = logging.getLogger(__name__)

DEFAULT_SKILLS = {
    "python", "java", "javascript", "typescript", "react", "next.js", "fastapi", "django", "flask",
    "sql", "postgresql", "mysql", "redis", "docker", "kubernetes", "aws", "azure", "gcp",
    "machine learning", "deep learning", "nlp", "transformers", "pytorch", "tensorflow", "scikit-learn",
    "pandas", "numpy", "spark", "airflow", "celery", "git", "ci/cd", "linux", "rest", "graphql",
    "leadership", "communication", "stakeholder management", "agile", "scrum",
}
SECTION_HEADERS = {
    "education": ("education", "academic"),
    "certifications": ("certifications", "certificates", "licenses"),
    "projects": ("projects", "portfolio"),
    "experience": ("experience", "employment", "work history", "professional experience"),
}
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.IGNORECASE)
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}")
YEARS_RE = re.compile(r"(\d+(?:\.\d+)?)\+?\s*(?:years|yrs)", re.IGNORECASE)
TITLE_RE = re.compile(r"\b(?:senior|staff|principal|lead|junior)?\s*(?:software|data|machine learning|ml|ai|frontend|backend|full stack|devops)\s+(?:engineer|scientist|developer|architect)\b", re.IGNORECASE)


@dataclass(slots=True)
class ParsedFile:
    file_name: str
    text: str


class ResumeParser:
    def __init__(self, skill_vocabulary: set[str] | None = None) -> None:
        self.skill_vocabulary = {s.lower() for s in (skill_vocabulary or DEFAULT_SKILLS)}

    def parse_upload(self, file_name: str, payload: bytes) -> ResumeProfile:
        suffix = Path(file_name).suffix.lower()
        if suffix == ".pdf":
            text = self._extract_pdf(payload)
        elif suffix == ".docx":
            text = self._extract_docx(payload)
        elif suffix in {".txt", ".md"}:
            text = payload.decode("utf-8", errors="ignore")
        else:
            raise ValueError(f"Unsupported resume file type: {suffix}")
        return self.parse_text(file_name=file_name, text=text)

    def parse_text(self, file_name: str, text: str) -> ResumeProfile:
        clean = self._normalize_text(text)
        contact = ContactInfo(name=self._extract_name(clean), email=self._first_match(EMAIL_RE, clean), phone=self._first_match(PHONE_RE, clean))
        skills = self._extract_skills(clean)
        return ResumeProfile(
            file_name=file_name,
            raw_text=clean,
            contact=contact,
            skills=skills,
            education=self._extract_section_lines(clean, "education"),
            certifications=self._extract_section_lines(clean, "certifications"),
            projects=self._extract_section_lines(clean, "projects"),
            job_titles=sorted({m.group(0).title() for m in TITLE_RE.finditer(clean)}),
            languages=self._extract_languages(clean),
            years_experience=self._extract_years(clean),
        )

    def _extract_pdf(self, payload: bytes) -> str:
        chunks: list[str] = []
        import pdfplumber

        with pdfplumber.open(io.BytesIO(payload)) as pdf:
            for page in pdf.pages:
                chunks.append(page.extract_text() or "")
        text = "\n".join(chunks).strip()
        if not text:
            LOGGER.warning("PDF text extraction returned no text; OCR fallback should be enabled in production image")
        return text

    def _extract_docx(self, payload: bytes) -> str:
        import docx

        document = docx.Document(io.BytesIO(payload))
        return "\n".join(paragraph.text for paragraph in document.paragraphs)

    def _normalize_text(self, text: str) -> str:
        return re.sub(r"[ \t]+", " ", text.replace("\x00", "")).strip()

    def _first_match(self, pattern: re.Pattern[str], text: str) -> str | None:
        match = pattern.search(text)
        return match.group(0) if match else None

    def _extract_name(self, text: str) -> str | None:
        for line in [line.strip() for line in text.splitlines() if line.strip()][:5]:
            if not EMAIL_RE.search(line) and len(line.split()) in {2, 3, 4} and not any(char.isdigit() for char in line):
                return line[:120]
        return None

    def _extract_skills(self, text: str) -> list[str]:
        lowered = text.lower()
        found = [skill for skill in self.skill_vocabulary if re.search(rf"(?<!\w){re.escape(skill)}(?!\w)", lowered)]
        return sorted(found)

    def _extract_section_lines(self, text: str, section: str) -> list[str]:
        headers = SECTION_HEADERS[section]
        lines = [line.strip(" •-\t") for line in text.splitlines() if line.strip()]
        collected: list[str] = []
        active = False
        for line in lines:
            lower = line.lower().rstrip(":")
            if any(h in lower for h in headers):
                active = True
                continue
            if active and any(any(h in lower for h in values) for key, values in SECTION_HEADERS.items() if key != section):
                break
            if active:
                collected.append(line)
                if len(collected) >= 8:
                    break
        return collected

    def _extract_years(self, text: str) -> float:
        values = [float(m.group(1)) for m in YEARS_RE.finditer(text)]
        return max(values, default=0.0)

    def _extract_languages(self, text: str) -> list[str]:
        candidates = ["english", "spanish", "french", "german", "hindi", "mandarin", "arabic", "portuguese"]
        lowered = text.lower()
        return sorted(lang.title() for lang in candidates if lang in lowered)
