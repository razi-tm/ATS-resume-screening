from __future__ import annotations

import json
import logging
import sys
from dataclasses import asdict
from pathlib import Path

import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
for pkg in ["shared-types", "resume-parser", "ai-engine", "scoring-engine"]:
    sys.path.insert(0, str(ROOT / "packages" / pkg))

from resume_parser import ResumeParser  # noqa: E402
from scoring_engine import ScreeningScorer  # noqa: E402
from shared_types import ScreeningWeights  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
LOGGER = logging.getLogger("streamlit_mvp")

st.set_page_config(page_title="ATS Resume Screening", page_icon="🧠", layout="wide")


@st.cache_resource(show_spinner=False)
def parser() -> ResumeParser:
    return ResumeParser()


@st.cache_resource(show_spinner=False)
def scorer(weights_tuple: tuple[float, float, float, float]) -> ScreeningScorer:
    return ScreeningScorer(weights=ScreeningWeights(*weights_tuple))


def read_job_upload(uploaded) -> str:
    if uploaded is None:
        return ""
    return uploaded.getvalue().decode("utf-8", errors="ignore")


def render_upload() -> None:
    st.title("AI-Powered ATS Resume Screening")
    st.caption("Upload resumes, paste a job description, and rank candidates using deterministic NLP scoring.")
    left, right = st.columns([2, 1])
    with left:
        resumes = st.file_uploader("Upload resumes (PDF, DOCX, TXT)", type=["pdf", "docx", "txt", "md"], accept_multiple_files=True)
        job_text = st.text_area("Job description", height=280, placeholder="Paste the role requirements, responsibilities, skills, and minimum experience...")
        job_file = st.file_uploader("Optional job description file", type=["txt", "md"])
        if job_file and not job_text:
            job_text = read_job_upload(job_file)
    with right:
        st.subheader("Scoring weights")
        semantic = st.slider("Semantic", 0.0, 1.0, 0.45, 0.05)
        keyword = st.slider("Keyword", 0.0, 1.0, 0.25, 0.05)
        skills = st.slider("Skills", 0.0, 1.0, 0.20, 0.05)
        experience = st.slider("Experience", 0.0, 1.0, 0.10, 0.05)
        st.info("Weights are normalized before scoring.")
    if st.button("Run screening", type="primary", disabled=not resumes or not job_text):
        parsed = []
        progress = st.progress(0, text="Parsing resumes")
        for index, uploaded in enumerate(resumes):
            parsed.append(parser().parse_upload(uploaded.name, uploaded.getvalue()))
            progress.progress((index + 1) / len(resumes), text=f"Parsed {uploaded.name}")
        scoring = scorer((semantic, keyword, skills, experience))
        job = scoring.build_job(job_text)
        st.session_state["results"] = scoring.score(parsed, job)
        st.session_state["job"] = asdict(job)
        st.success(f"Screened {len(parsed)} candidates")


def render_results() -> None:
    st.header("Screening Results")
    results = st.session_state.get("results", [])
    if not results:
        st.warning("Run a screening from Upload & Configuration first.")
        return
    rows = [asdict(result) | {"rank": rank} for rank, result in enumerate(results, start=1)]
    df = pd.DataFrame(rows)
    st.dataframe(df[["rank", "candidate_name", "file_name", "final_score", "semantic_score", "keyword_score", "skills_score", "experience_score"]], use_container_width=True, hide_index=True)
    st.download_button("Download CSV", df.to_csv(index=False).encode("utf-8"), "screening-results.csv", "text/csv")
    st.download_button("Download JSON", json.dumps(rows, default=str, indent=2), "screening-results.json", "application/json")
    for rank, result in enumerate(results, start=1):
        with st.expander(f"#{rank} {result.candidate_name} — {result.final_score}%"):
            st.progress(min(result.final_score / 100, 1.0), text="Final ATS compatibility")
            c1, c2 = st.columns(2)
            c1.write("**Matched skills**")
            c1.write(", ".join(result.matched_skills) or "None detected")
            c2.write("**Missing skills**")
            c2.write(", ".join(result.missing_skills) or "None")
            st.write("**Explanation**")
            for item in result.explanations:
                st.write(f"- {item}")


def render_deep_dive() -> None:
    st.header("Candidate Deep Dive")
    results = st.session_state.get("results", [])
    if not results:
        st.warning("No candidates available yet.")
        return
    selected = st.selectbox("Candidate", results, format_func=lambda r: f"{r.candidate_name} ({r.final_score}%)")
    data = selected.extracted_data
    c1, c2, c3 = st.columns(3)
    c1.metric("Final score", f"{selected.final_score}%")
    c2.metric("Years experience", data.get("years_experience", 0))
    c3.metric("Detected skills", len(data.get("skills", [])))
    st.json(data, expanded=False)
    st.subheader("Resume text preview")
    st.text(data.get("raw_text", "")[:5000])


def render_analytics() -> None:
    st.header("Analytics")
    results = st.session_state.get("results", [])
    if not results:
        st.warning("No analytics until screening has run.")
        return
    df = pd.DataFrame([asdict(result) for result in results])
    st.bar_chart(df.set_index("candidate_name")[["final_score", "semantic_score", "keyword_score"]])
    missing = pd.Series([skill for result in results for skill in result.missing_skills]).value_counts().head(10)
    if not missing.empty:
        st.subheader("Most common missing skills")
        st.bar_chart(missing)


PAGES = {
    "Upload & Configuration": render_upload,
    "Screening Results": render_results,
    "Candidate Deep Dive": render_deep_dive,
    "Analytics": render_analytics,
}
page = st.sidebar.radio("Navigation", list(PAGES))
PAGES[page]()
