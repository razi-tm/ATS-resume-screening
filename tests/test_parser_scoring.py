from ai_engine import SkillInferenceProvider, SkillInferenceResult
from resume_parser import ResumeParser
from scoring_engine import ScreeningScorer


class FrameworkSkillInferenceProvider(SkillInferenceProvider):
    def infer_matches(
        self,
        *,
        job_description: str,
        resume_text: str,
        required_skills: list[str],
        detected_skills: list[str],
        direct_matches: list[str],
    ) -> SkillInferenceResult:
        evidence = {}
        detected = set(detected_skills)
        if "python" in required_skills and {"fastapi", "django"} & detected:
            evidence["python"] = "FastAPI/Django project evidence implies Python experience."
        if "typescript" in required_skills and "react" in detected:
            evidence["typescript"] = "React application evidence supports TypeScript capability."
        return SkillInferenceResult(matched_skills=evidence)


def test_parser_extracts_contact_and_skills() -> None:
    text = """Alex Morgan\nalex@example.com | 415-555-0198\nPython FastAPI Docker NLP\nExperience\n6+ years building ML systems"""
    profile = ResumeParser().parse_text("alex.txt", text)
    assert profile.contact.email == "alex@example.com"
    assert "python" in profile.skills
    assert profile.years_experience == 6


def test_scorer_ranks_relevant_resume_first() -> None:
    parser = ResumeParser()
    resumes = [
        parser.parse_text("ml.txt", "Python NLP transformers FastAPI Docker PostgreSQL AWS 6+ years Alex Morgan"),
        parser.parse_text("frontend.txt", "React CSS design systems 2+ years Jordan Lee"),
    ]
    job = ScreeningScorer().build_job("Need 5+ years Python NLP transformers FastAPI Docker PostgreSQL AWS")
    results = ScreeningScorer().score(resumes, job)
    assert results[0].file_name == "ml.txt"
    assert results[0].final_score > results[1].final_score


def test_parser_keeps_detected_skills_separate_from_inferred_skills() -> None:
    text = "Built production services with FastAPI and Django; shipped React applications."
    profile = ResumeParser().parse_text("frameworks.txt", text)

    assert "fastapi" in profile.skills
    assert "django" in profile.skills
    assert "react" in profile.skills
    assert "python" not in profile.skills
    assert "typescript" not in profile.skills


def test_scorer_credits_llm_or_nlp_skill_inference_for_language_requirements() -> None:
    parser = ResumeParser()
    resumes = [
        parser.parse_text("frameworks.txt", "FastAPI Django React PostgreSQL Docker 5+ years Sam Rivera"),
        parser.parse_text("keywords.txt", "Python TypeScript 2+ years Casey Kim"),
    ]
    scorer = ScreeningScorer(skill_inference_provider=FrameworkSkillInferenceProvider())
    job = scorer.build_job("Need 5+ years Python TypeScript PostgreSQL Docker")
    results = scorer.score(resumes, job)
    framework_result = next(result for result in results if result.file_name == "frameworks.txt")

    assert results[0].file_name == "frameworks.txt"
    assert "python" in framework_result.matched_skills
    assert "typescript" in framework_result.matched_skills
    assert "python" not in framework_result.missing_skills
    assert "typescript" not in framework_result.missing_skills
    assert framework_result.extracted_data["inferred_skill_evidence"] == {
        "python": "FastAPI/Django project evidence implies Python experience.",
        "typescript": "React application evidence supports TypeScript capability.",
    }


def test_default_tfidf_skill_inference_uses_contextual_evidence_not_manual_rules() -> None:
    parser = ResumeParser()
    resumes = [
        parser.parse_text("frameworks.txt", "FastAPI Django React PostgreSQL Docker 5+ years Sam Rivera"),
        parser.parse_text("keywords.txt", "Python TypeScript 2+ years Casey Kim"),
    ]
    scorer = ScreeningScorer()
    job = scorer.build_job("Need 5+ years Python TypeScript PostgreSQL Docker")
    results = scorer.score(resumes, job)
    framework_result = next(result for result in results if result.file_name == "frameworks.txt")
    keyword_result = next(result for result in results if result.file_name == "keywords.txt")

    assert results[0].file_name == "frameworks.txt"
    assert {"python", "typescript"}.issubset(framework_result.matched_skills)
    assert {"docker", "postgresql"}.issubset(keyword_result.missing_skills)
    assert "contextual TF-IDF evidence" in framework_result.explanations[3]
