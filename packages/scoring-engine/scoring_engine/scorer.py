from __future__ import annotations

import math
import re
from dataclasses import asdict

from ai_engine import EmbeddingProvider, SkillInferenceProvider, get_embedding_provider, get_skill_inference_provider
from resume_parser import DEFAULT_SKILLS, SKILL_ALIASES
from shared_types import CandidateScore, JobDescription, ResumeProfile, ScreeningWeights


class ScreeningScorer:
    def __init__(
        self,
        embedding_provider: EmbeddingProvider | None = None,
        weights: ScreeningWeights | None = None,
        skill_inference_provider: SkillInferenceProvider | None = None,
    ) -> None:
        self.embedding_provider = embedding_provider or get_embedding_provider()
        self.skill_inference_provider = skill_inference_provider or get_skill_inference_provider()
        self.weights = (weights or ScreeningWeights()).normalized()

    def score(self, resumes: list[ResumeProfile], job: JobDescription) -> list[CandidateScore]:
        if not resumes:
            return []
        required = set(job.required_skills or self.extract_skills(job.description))
        job_context = self._scoring_context(job.description, required, "Required skills")
        resume_contexts = [
            self._scoring_context(resume.raw_text, set(resume.skills), "Detected skills") for resume in resumes
        ]
        corpus = [job_context, *resume_contexts]
        embeddings = self.embedding_provider.embed(corpus)
        job_vec = embeddings[0]
        resume_vecs = embeddings[1:]
        results: list[CandidateScore] = []
        for resume, vector, resume_context in zip(resumes, resume_vecs, resume_contexts, strict=True):
            semantic = self._cosine(job_vec, vector)
            keyword = self._keyword_overlap(resume_context, job_context)
            direct_matches = set(resume.skills) & required
            inferred_matches = self.skill_inference_provider.infer_matches(
                job_description=job.description,
                resume_text=resume.raw_text,
                required_skills=sorted(required),
                detected_skills=resume.skills,
                direct_matches=sorted(direct_matches),
            ).matched_skills
            matched = sorted(direct_matches | set(inferred_matches))
            missing = sorted(required - set(matched))
            skills_score = len(matched) / max(len(required), 1)
            experience_score = min(resume.years_experience / max(job.min_years_experience, 1.0), 1.0)
            final = (
                self.weights.semantic * semantic
                + self.weights.keyword * keyword
                + self.weights.skills * skills_score
                + self.weights.experience * experience_score
            )
            explanations = self._explain(resume, semantic, keyword, matched, missing, experience_score, inferred_matches)
            results.append(CandidateScore(
                resume_id=resume.id,
                candidate_name=resume.contact.name or resume.file_name,
                file_name=resume.file_name,
                final_score=round(final * 100, 2),
                semantic_score=round(semantic * 100, 2),
                keyword_score=round(keyword * 100, 2),
                skills_score=round(skills_score * 100, 2),
                experience_score=round(experience_score * 100, 2),
                matched_skills=matched,
                missing_skills=missing,
                explanations=explanations,
                extracted_data=asdict(resume) | {"inferred_skill_evidence": inferred_matches},
            ))
        return sorted(results, key=lambda score: score.final_score, reverse=True)

    def extract_skills(self, text: str) -> list[str]:
        lowered = text.lower()
        return sorted(skill for skill in DEFAULT_SKILLS if self._has_skill(lowered, skill))

    def build_job(self, description: str, title: str = "") -> JobDescription:
        return JobDescription(title=title, description=description, required_skills=self.extract_skills(description), min_years_experience=self._extract_min_years(description))

    def _scoring_context(self, text: str, skills: set[str], label: str) -> str:
        if not skills:
            return text
        return f"{text}\n{label}: {' '.join(sorted(skills))}"

    def _has_skill(self, lowered_text: str, skill: str) -> bool:
        skill_terms = (skill, *SKILL_ALIASES.get(skill, ()))
        return any(re.search(rf"(?<!\w){re.escape(term)}(?!\w)", lowered_text) for term in skill_terms)

    def _cosine(self, left: list[float], right: list[float]) -> float:
        if not left or not right or len(left) != len(right):
            return 0.0
        denominator = math.sqrt(sum(value * value for value in left)) * math.sqrt(sum(value * value for value in right))
        if math.isclose(denominator, 0.0):
            return 0.0
        return max(0.0, min(1.0, sum(left_value * right_value for left_value, right_value in zip(left, right, strict=True)) / denominator))

    def _keyword_overlap(self, resume_text: str, job_text: str) -> float:
        def tokens(value: str) -> set[str]:
            return {t for t in re.findall(r"[a-zA-Z][a-zA-Z+#.]{2,}", value.lower()) if t not in {"and", "the", "with", "for", "from"}}
        job_tokens = tokens(job_text)
        if not job_tokens:
            return 0.0
        return len(tokens(resume_text) & job_tokens) / len(job_tokens)

    def _extract_min_years(self, text: str) -> float:
        values = [float(match.group(1)) for match in re.finditer(r"(\d+(?:\.\d+)?)\+?\s*(?:years|yrs)", text, re.IGNORECASE)]
        return max(values, default=0.0)

    def _explain(
        self,
        resume: ResumeProfile,
        semantic: float,
        keyword: float,
        matched: list[str],
        missing: list[str],
        experience_score: float,
        inferred_matches: dict[str, str],
    ) -> list[str]:
        explanations = [
            f"Semantic similarity is {semantic:.0%}, indicating {'strong' if semantic >= .7 else 'moderate' if semantic >= .45 else 'limited'} contextual alignment.",
            f"Keyword overlap is {keyword:.0%} across the job description vocabulary.",
            f"Matched {len(matched)} required skills: {', '.join(matched[:8]) or 'none detected'}.",
            f"Missing or weak skills: {', '.join(missing[:8]) or 'none'}.",
            f"Experience evidence is {'sufficient' if experience_score >= 1 else 'below requested threshold'} based on extracted years ({resume.years_experience:g}).",
        ]
        if inferred_matches:
            evidence = "; ".join(f"{skill}: {reason}" for skill, reason in sorted(inferred_matches.items()))
            explanations.insert(3, f"Inferred skill matches from AI/NLP evidence: {evidence}.")
        return explanations
