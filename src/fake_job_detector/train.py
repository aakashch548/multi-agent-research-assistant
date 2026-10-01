"""Training and evaluation."""

from __future__ import annotations

import json
from pathlib import Path

import joblib
import nltk
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.naive_bayes import MultinomialNB
from sklearn.tree import DecisionTreeClassifier

from fake_job_detector.config import TrainConfig
from fake_job_detector.preprocessing import load_raw_csv, prepare_dataset


def ensure_nltk_stopwords() -> None:
    try:
        nltk.data.find("corpora/stopwords")
    except LookupError:
        nltk.download("stopwords", quiet=True)


def train_models(config: TrainConfig) -> dict:
    ensure_nltk_stopwords()
    config.ensure_dirs()

    raw = load_raw_csv(config.data_path)
    texts, labels = prepare_dataset(raw, random_state=config.random_state)

    split_kwargs: dict = {
        "test_size": config.test_size,
        "random_state": config.random_state,
    }
    if len(labels) >= 10 and labels.value_counts().min() >= 2:
        split_kwargs["stratify"] = labels
    X_train, X_test, y_train, y_test = train_test_split(texts, labels, **split_kwargs)

    vectorizer = CountVectorizer(max_features=config.max_features)
    X_train_dtm = vectorizer.fit_transform(X_train)
    X_test_dtm = vectorizer.transform(X_test)

    nb = MultinomialNB()
    nb.fit(X_train_dtm, y_train)
    y_pred_nb = nb.predict(X_test_dtm)

    dt = DecisionTreeClassifier(random_state=config.random_state)
    dt.fit(X_train_dtm, y_train)
    y_pred_dt = dt.predict(X_test_dtm)

    metrics = {
        "naive_bayes": _metrics_dict(y_test, y_pred_nb),
        "decision_tree": _metrics_dict(y_test, y_pred_dt),
        "train_size": int(len(X_train)),
        "test_size": int(len(X_test)),
    }

    joblib.dump(vectorizer, config.models_dir / "vectorizer.joblib")
    joblib.dump(nb, config.models_dir / "naive_bayes.joblib")
    joblib.dump(dt, config.models_dir / "decision_tree.joblib")
    (config.models_dir / "metrics.json").write_text(
        json.dumps(metrics, indent=2),
        encoding="utf-8",
    )
    return metrics


def _metrics_dict(y_true, y_pred) -> dict:
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "classification_report": classification_report(y_true, y_pred, output_dict=True),
        "confusion_matrix": confusion_matrix(y_true, y_pred).tolist(),
    }
