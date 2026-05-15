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
