from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.naive_bayes import MultinomialNB
import joblib

from fake_job_detector.config import TrainConfig
from fake_job_detector.predict import JobPostingClassifier
from fake_job_detector.train import train_models


def test_train_and_predict_roundtrip(sample_job_frame, tmp_path: Path):
    csv_path = tmp_path / "jobs.csv"
    sample_job_frame.to_csv(csv_path, index=False)
    models_dir = tmp_path / "models"

    metrics = train_models(
        TrainConfig(data_path=csv_path, models_dir=models_dir, test_size=0.25, random_state=0)
    )
    assert "naive_bayes" in metrics
    assert (models_dir / "vectorizer.joblib").is_file()

    clf = JobPostingClassifier(models_dir=models_dir)
    result = clf.predict("Make thousands of dollars from home with no experience")
    assert "label" in result
    assert isinstance(result["is_fraudulent"], bool)


def test_minimal_joblib_load(tmp_path: Path):
    vect = CountVectorizer()
    X = vect.fit_transform(["real job posting", "fake urgent money"])
    model = MultinomialNB()
    model.fit(X, [0, 1])
    joblib.dump(vect, tmp_path / "vectorizer.joblib")
    joblib.dump(model, tmp_path / "naive_bayes.joblib")

    clf = JobPostingClassifier(models_dir=tmp_path)
    out = clf.predict("urgent money wire transfer")
    assert out["label"] in (0, 1)
