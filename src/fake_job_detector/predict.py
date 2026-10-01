"""Load artifacts and classify job posting text."""

from __future__ import annotations

from pathlib import Path

import joblib
import nltk
from nltk.corpus import stopwords

from fake_job_detector.config import DEFAULT_MODEL_NAME, PROJECT_ROOT


class JobPostingClassifier:
    def __init__(
        self,
        models_dir: Path | None = None,
        model_name: str = DEFAULT_MODEL_NAME,
    ) -> None:
        self.models_dir = models_dir or (PROJECT_ROOT / "models")
        self.model_name = model_name
        self._vectorizer = None
        self._model = None

    def _ensure_stopwords(self) -> None:
        try:
            nltk.data.find("corpora/stopwords")
        except LookupError:
            nltk.download("stopwords", quiet=True)

    def load(self) -> None:
        suffix = f"{self.model_name}.joblib"
        model_path = self.models_dir / suffix
        vectorizer_path = self.models_dir / "vectorizer.joblib"
        if not model_path.is_file():
            raise FileNotFoundError(
                f"Model not found at {model_path}. Run scripts/train.py first."
            )
        self._vectorizer = joblib.load(vectorizer_path)
        self._model = joblib.load(model_path)

    def _preprocess(self, text: str) -> str:
        self._ensure_stopwords()
        stops = set(stopwords.words("english"))
        lowered = text.lower()
        return " ".join(word for word in lowered.split() if word not in stops)

    def predict(self, text: str) -> dict:
        if self._vectorizer is None or self._model is None:
            self.load()
        cleaned = self._preprocess(text)
        features = self._vectorizer.transform([cleaned])
        label = int(self._model.predict(features)[0])
        proba = None
        if hasattr(self._model, "predict_proba"):
            proba = float(self._model.predict_proba(features)[0][label])
        return {
            "label": label,
            "is_fraudulent": label == 1,
            "display": "Fraudulent job posting" if label == 1 else "Legitimate job posting",
            "confidence": proba,
        }
