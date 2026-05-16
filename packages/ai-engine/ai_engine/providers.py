from __future__ import annotations

import abc
import json
import os
from dataclasses import dataclass, field
from functools import lru_cache

Vector = list[float]


@dataclass(slots=True)
class SkillInferenceResult:
    """Evidence that a resume satisfies a required skill beyond exact keyword matching."""

    matched_skills: dict[str, str] = field(default_factory=dict)


class EmbeddingProvider(abc.ABC):
    @abc.abstractmethod
    def embed(self, texts: list[str]) -> list[Vector]:
        raise NotImplementedError


class SentenceTransformerProvider(EmbeddingProvider):
    def __init__(self, model_name: str = "sentence-transformers/all-mpnet-base-v2") -> None:
        from sentence_transformers import SentenceTransformer

        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: list[str]) -> list[Vector]:
        return self.model.encode(texts, normalize_embeddings=True).tolist()


class TfidfEmbeddingProvider(EmbeddingProvider):
    """Word + character n-gram TF-IDF fallback for constrained environments."""

    def __init__(self, max_features: int = 4096) -> None:
        self.max_features = max_features

    def embed(self, texts: list[str]) -> list[Vector]:
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.pipeline import FeatureUnion

        vectorizer = FeatureUnion(
            [
                (
                    "word",
                    TfidfVectorizer(
                        lowercase=True,
                        ngram_range=(1, 2),
                        stop_words="english",
                        token_pattern=r"(?u)\b[a-zA-Z][a-zA-Z0-9+#.\-/]{1,}\b",
                        max_features=self.max_features,
                        sublinear_tf=True,
                    ),
                ),
                (
                    "char",
                    TfidfVectorizer(
                        analyzer="char_wb",
                        lowercase=True,
                        ngram_range=(3, 5),
                        max_features=self.max_features,
                        sublinear_tf=True,
                    ),
                ),
            ]
        )
        matrix = vectorizer.fit_transform(texts)
        return matrix.toarray().tolist()


class SkillInferenceProvider(abc.ABC):
    @abc.abstractmethod
    def infer_matches(
        self,
        *,
        job_description: str,
        resume_text: str,
        required_skills: list[str],
        detected_skills: list[str],
        direct_matches: list[str],
    ) -> SkillInferenceResult:
        raise NotImplementedError


class DisabledSkillInferenceProvider(SkillInferenceProvider):
    def infer_matches(
        self,
        *,
        job_description: str,
        resume_text: str,
        required_skills: list[str],
        detected_skills: list[str],
        direct_matches: list[str],
    ) -> SkillInferenceResult:
        return SkillInferenceResult()


class TfidfSkillInferenceProvider(SkillInferenceProvider):
    """Infer contextual skill matches without a hand-written skill-to-skill map.

    The provider compares each missing required skill in its job context against the
    candidate's resume context using the same word + character TF-IDF strategy as
    the default embedding provider. It is intentionally conservative and only
    credits a missing skill when the resume already has directly detected technical
    evidence and the contextual similarity clears a configurable threshold.
    """

    def __init__(self, threshold: float | None = None) -> None:
        self.threshold = threshold if threshold is not None else float(os.getenv("TFIDF_SKILL_MATCH_THRESHOLD", "0.34"))
        self.embedding_provider = TfidfEmbeddingProvider()

    def infer_matches(
        self,
        *,
        job_description: str,
        resume_text: str,
        required_skills: list[str],
        detected_skills: list[str],
        direct_matches: list[str],
    ) -> SkillInferenceResult:
        direct = set(direct_matches)
        supporting_skills = sorted(set(detected_skills) - direct)
        missing = [skill for skill in required_skills if skill not in direct]
        if not missing or not supporting_skills:
            return SkillInferenceResult()

        matched: dict[str, str] = {}
        resume_context = self._resume_context(resume_text, supporting_skills)
        for skill in missing:
            job_context = self._job_skill_context(job_description, skill)
            score = self._similarity(job_context, resume_context)
            if score >= self.threshold:
                matched[skill] = f"contextual TF-IDF evidence ({score:.0%} similarity)"
        return SkillInferenceResult(matched_skills=matched)

    def _similarity(self, left: str, right: str) -> float:
        left_vec, right_vec = self.embedding_provider.embed([left, right])
        numerator = sum(left_value * right_value for left_value, right_value in zip(left_vec, right_vec, strict=True))
        return max(0.0, min(1.0, numerator))

    def _job_skill_context(self, job_description: str, skill: str) -> str:
        snippets = self._snippets(job_description, skill)
        return "\n".join(snippets) if snippets else f"Required skill: {skill}\n{job_description}"

    def _resume_context(self, resume_text: str, detected_skills: list[str]) -> str:
        snippets: list[str] = []
        for skill in detected_skills:
            snippets.extend(self._snippets(resume_text, skill))
        return "\n".join(snippets[:16]) if snippets else resume_text

    def _snippets(self, text: str, phrase: str, window: int = 140) -> list[str]:
        lowered = text.lower()
        phrase = phrase.lower()
        snippets = []
        start = 0
        while True:
            index = lowered.find(phrase, start)
            if index == -1:
                break
            snippets.append(text[max(0, index - window) : index + len(phrase) + window])
            start = index + len(phrase)
        return snippets


class OpenAISkillInferenceProvider(SkillInferenceProvider):
    """Use an LLM to infer whether resume evidence satisfies required skills."""

    def __init__(self, model: str | None = None) -> None:
        from openai import OpenAI

        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model or os.getenv("OPENAI_SKILL_INFERENCE_MODEL", "gpt-4.1-mini")

    def infer_matches(
        self,
        *,
        job_description: str,
        resume_text: str,
        required_skills: list[str],
        detected_skills: list[str],
        direct_matches: list[str],
    ) -> SkillInferenceResult:
        prompt = {
            "task": "Return required skills that are satisfied by the resume even when the exact words are absent.",
            "rules": [
                "Use concrete resume evidence only.",
                "Infer technologies from frameworks, libraries, projects, and responsibilities when technically justified.",
                "Do not infer a skill from vague seniority or unrelated tools.",
                "Return strict JSON: {\"matched_skills\": {\"required skill\": \"short evidence\"}}.",
            ],
            "required_skills": required_skills,
            "detected_skills": detected_skills,
            "direct_matches": direct_matches,
            "missing_required_skills": [skill for skill in required_skills if skill not in set(direct_matches)],
            "job_description": job_description[:5000],
            "resume_text": resume_text[:8000],
        }
        response = self.client.responses.create(
            model=self.model,
            input=json.dumps(prompt),
        )
        try:
            parsed = json.loads(response.output_text)
        except json.JSONDecodeError:
            return SkillInferenceResult()
        matches = parsed.get("matched_skills", {})
        if not isinstance(matches, dict):
            return SkillInferenceResult()
        allowed = {skill.lower(): skill for skill in required_skills}
        inferred: dict[str, str] = {}
        for skill, evidence in matches.items():
            normalized_skill = str(skill).lower()
            if normalized_skill in allowed:
                inferred[allowed[normalized_skill]] = str(evidence)
        return SkillInferenceResult(matched_skills=inferred)


class LLMProvider(abc.ABC):
    @abc.abstractmethod
    def summarize_fit(self, resume_text: str, job_description: str) -> str:
        raise NotImplementedError


class DisabledLLMProvider(LLMProvider):
    def summarize_fit(self, resume_text: str, job_description: str) -> str:
        return "LLM enhancement is disabled; deterministic scoring explanation is shown."


class OpenAIProvider(LLMProvider):
    def __init__(self, model: str = "gpt-4.1-mini") -> None:
        from openai import OpenAI

        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = model

    def summarize_fit(self, resume_text: str, job_description: str) -> str:
        response = self.client.responses.create(
            model=self.model,
            input=f"Assess candidate fit briefly.\nJOB:\n{job_description[:4000]}\nRESUME:\n{resume_text[:6000]}",
        )
        return response.output_text


@lru_cache(maxsize=1)
def get_embedding_provider() -> EmbeddingProvider:
    provider = os.getenv("EMBEDDING_PROVIDER", "tfidf").lower()
    if provider == "sentence-transformers":
        return SentenceTransformerProvider(os.getenv("EMBEDDING_MODEL", "sentence-transformers/all-mpnet-base-v2"))
    return TfidfEmbeddingProvider()


@lru_cache(maxsize=1)
def get_skill_inference_provider() -> SkillInferenceProvider:
    provider = os.getenv("SKILL_INFERENCE_PROVIDER", "tfidf").lower()
    if provider == "openai":
        return OpenAISkillInferenceProvider()
    if provider == "disabled":
        return DisabledSkillInferenceProvider()
    return TfidfSkillInferenceProvider()
