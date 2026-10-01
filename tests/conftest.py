import nltk
import pandas as pd
import pytest


@pytest.fixture(scope="session", autouse=True)
def _nltk_stopwords():
    try:
        nltk.data.find("corpora/stopwords")
    except LookupError:
        nltk.download("stopwords", quiet=True)


@pytest.fixture
def sample_job_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "job_id": [1, 2, 3, 4],
            "title": ["Engineer", "Scam job", "Analyst", "Easy money"],
            "location": ["US, TX", "Remote", "US, NY", "Anywhere"],
            "department": ["IT", " ", "Data", " "],
            "salary_range": [None, None, None, None],
            "company_profile": ["Tech co", " ", "Finance", " "],
            "description": [
                "Build APIs with Python",
                "Make thousands weekly no work",
                "SQL and dashboards",
                "Wire fee to start today",
            ],
            "requirements": ["3 yrs Python", "None", "SQL", "None"],
            "benefits": ["Health", " ", "401k", " "],
            "telecommuting": [0, 1, 0, 1],
            "has_company_logo": [1, 0, 1, 0],
            "has_questions": [1, 0, 0, 0],
            "employment_type": ["Full-time", " ", "Full-time", " "],
            "required_experience": ["Mid", " ", "Entry", " "],
            "required_education": ["BS", " ", "BS", " "],
            "industry": ["Software", " ", "Finance", " "],
            "function": ["Engineering", " ", "Analytics", " "],
            "fraudulent": [0, 1, 0, 1],
        }
    )
