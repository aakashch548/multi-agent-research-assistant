from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]

COLUMNS_TO_DROP = [
    "job_id",
    "salary_range",
    "telecommuting",
    "has_company_logo",
    "has_questions",
]

TEXT_COLUMNS = [
    "title",
    "location",
    "company_profile",
    "description",
    "requirements",
    "benefits",
    "industry",
]

TARGET_COLUMN = "fraudulent"


@dataclass(frozen=True)
class TrainConfig:
    data_path: Path
    models_dir: Path = PROJECT_ROOT / "models"
    test_size: float = 0.3
    random_state: int = 42
    max_features: int | None = None

    def ensure_dirs(self) -> None:
        self.models_dir.mkdir(parents=True, exist_ok=True)


DEFAULT_MODEL_NAME = "naive_bayes"
