"""Streamlit UI for fake job posting detection."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import streamlit as st

from fake_job_detector.predict import JobPostingClassifier

st.set_page_config(page_title="Fake Job Detector", page_icon="🔍", layout="centered")

st.title("Fake Job Posting Detector")
st.caption(
    "Paste a job title and description. The model flags common scam patterns "
    "(unrealistic pay, urgency, work-from-home bait)."
)

model_choice = st.selectbox(
    "Model",
    options=("naive_bayes", "decision_tree"),
    format_func=lambda x: "Multinomial Naive Bayes" if x == "naive_bayes" else "Decision Tree",
)

sample_real = (
    "We are hiring a mid-level Python developer to build internal APIs. "
    "Requirements: 3+ years experience, BS in CS or equivalent, on-site in Austin."
)
sample_fake = (
    "URGENT! Earn $5000 per week working from home. No interview, no experience. "
    "Wire transfer fee required to start. Limited spots!"
)

if "job_text" not in st.session_state:
    st.session_state.job_text = ""

col1, col2 = st.columns(2)
with col1:
    if st.button("Load legitimate example"):
        st.session_state.job_text = sample_real
with col2:
    if st.button("Load suspicious example"):
        st.session_state.job_text = sample_fake

text = st.text_area(
    "Job posting text",
    height=220,
    key="job_text",
)

if st.button("Analyze", type="primary"):
    if not text.strip():
        st.warning("Enter some job posting text first.")
    else:
        try:
            clf = JobPostingClassifier(model_name=model_choice)
            result = clf.predict(text)
            if result["is_fraudulent"]:
                st.error(result["display"])
            else:
                st.success(result["display"])
            if result["confidence"] is not None:
                st.metric("Confidence (predicted class)", f"{result['confidence']:.1%}")
        except FileNotFoundError as exc:
            st.error(str(exc))
            st.info("Run `python scripts/train.py` after placing the dataset in `data/raw/`.")
