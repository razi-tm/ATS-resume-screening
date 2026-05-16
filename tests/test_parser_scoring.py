from resume_parser import ResumeParser
from scoring_engine import ScreeningScorer


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


def test_parser_infers_languages_from_framework_skills() -> None:
    text = "Built production services with FastAPI and Django; shipped React applications."
    profile = ResumeParser().parse_text("frameworks.txt", text)

    assert "fastapi" in profile.skills
    assert "django" in profile.skills
    assert "react" in profile.skills
    assert "python" in profile.skills
    assert "typescript" in profile.skills


def test_scorer_credits_frameworks_for_language_requirements() -> None:
    parser = ResumeParser()
    resumes = [
        parser.parse_text("frameworks.txt", "FastAPI Django React PostgreSQL Docker 5+ years Sam Rivera"),
        parser.parse_text("keywords.txt", "Python TypeScript 2+ years Casey Kim"),
    ]
    job = ScreeningScorer().build_job("Need 5+ years Python TypeScript PostgreSQL Docker")
    results = ScreeningScorer().score(resumes, job)
    framework_result = next(result for result in results if result.file_name == "frameworks.txt")

    assert results[0].file_name == "frameworks.txt"
    assert "python" in framework_result.matched_skills
    assert "typescript" in framework_result.matched_skills
    assert "python" not in framework_result.missing_skills
    assert "typescript" not in framework_result.missing_skills
