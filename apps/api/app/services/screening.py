from __future__ import annotations

import sys
from pathlib import Path
from dataclasses import asdict

ROOT = Path(__file__).resolve().parents[4]
for pkg in ["shared-types", "resume-parser", "ai-engine", "scoring-engine"]:
    sys.path.insert(0, str(ROOT / "packages" / pkg))

from resume_parser import ResumeParser  # noqa: E402
from scoring_engine import ScreeningScorer  # noqa: E402


class ScreeningService:
    def __init__(self) -> None:
        self.parser = ResumeParser()
        self.scorer = ScreeningScorer()

    def screen_texts(self, job_description: str, resumes: dict[str, str]) -> list[dict]:
        profiles = [self.parser.parse_text(file_name=name, text=text) for name, text in resumes.items()]
        job = self.scorer.build_job(job_description)
        return [asdict(result) for result in self.scorer.score(profiles, job)]
