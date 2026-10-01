"""Load and preprocess job posting data."""

from __future__ import annotations

import pandas as pd
from imblearn.under_sampling import RandomUnderSampler
from nltk.corpus import stopwords

from fake_job_detector.config import COLUMNS_TO_DROP, TARGET_COLUMN, TEXT_COLUMNS


def load_raw_csv(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path)


def drop_unused_columns(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    to_drop = [c for c in COLUMNS_TO_DROP if c in out.columns]
    out = out.drop(columns=to_drop)
    return out


def fill_missing_text(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out.fillna(" ", inplace=True)
    return out


def build_combined_text(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    missing = [c for c in TEXT_COLUMNS if c not in out.columns]
    if missing:
        raise ValueError(f"Dataset missing expected text columns: {missing}")
    if TARGET_COLUMN not in out.columns:
        raise ValueError(f"Dataset missing target column '{TARGET_COLUMN}'")

    out["text"] = (
        out["title"].astype(str)
        + " "
        + out["location"].astype(str)
        + " "
        + out["company_profile"].astype(str)
        + " "
        + out["description"].astype(str)
        + " "
        + out["requirements"].astype(str)
        + " "
        + out["benefits"].astype(str)
        + " "
        + out["industry"].astype(str)
    )
    return out[["text", TARGET_COLUMN]]


def normalize_text(series: pd.Series) -> pd.Series:
    stops = set(stopwords.words("english"))
    lowered = series.str.lower()
    return lowered.apply(
        lambda x: " ".join(word for word in x.split() if word not in stops)
    )


def balance_classes(
    texts: pd.Series,
    labels: pd.Series,
    random_state: int = 42,
) -> tuple[pd.Series, pd.Series]:
    """Undersample majority class (same strategy as reference notebook)."""
    frame = pd.DataFrame({"text": texts, TARGET_COLUMN: labels})
    X = frame[["text"]]
    y = frame[TARGET_COLUMN]
    sampler = RandomUnderSampler(random_state=random_state)
    X_res, y_res = sampler.fit_resample(X, y)
    return X_res["text"], y_res


def prepare_dataset(df: pd.DataFrame, random_state: int = 42) -> tuple[pd.Series, pd.Series]:
    """Full preprocessing pipeline from raw dataframe to balanced text + labels."""
    cleaned = drop_unused_columns(df)
    cleaned = fill_missing_text(cleaned)
    narrow = build_combined_text(cleaned)
    narrow["text"] = normalize_text(narrow["text"])
    return balance_classes(narrow["text"], narrow[TARGET_COLUMN], random_state=random_state)
