# Fake Job Posting Detection

Machine learning pipeline to classify online job postings as **legitimate** or **fraudulent**, based on text features from job descriptions and metadata.

This project refactors and productionizes the exploratory workflow from [Fake-job-detection-using-machine-learning](https://github.com/Aakash549/Fake-job-detection-using-machine-learning) into a reproducible, testable layout suitable for portfolio and deployment use.

## Problem

Fraudulent job listings often use vague promises, urgency, and minimal employer detail. The model learns patterns from labeled postings (typically the [Real / Fake Job Posting Prediction](https://www.kaggle.com/datasets/shivamb/real-or-fake-fake-jobposting-prediction) dataset) to flag suspicious listings before candidates apply.

## Features

- Configurable data path and training hyperparameters
- Text preprocessing: field merging, lowercasing, English stopword removal
- Class balancing with random undersampling
- **Multinomial Naive Bayes** (primary) and **Decision Tree** (baseline) classifiers
- Saved `joblib` artifacts for batch and interactive inference
- Streamlit demo UI
- Unit tests with synthetic samples (no dataset required for CI)

## Project structure

```
├── app/                    # Streamlit inference UI
├── data/raw/               # Place dataset CSV here (not committed)
├── models/                 # Trained vectorizer + classifiers
├── scripts/                # CLI entry points
├── src/fake_job_detector/  # Library code
└── tests/
```

## Dataset

1. Download `fake_job_posting.csv` from [Kaggle](https://www.kaggle.com/datasets/shivamb/real-or-fake-fake-jobposting-prediction).
2. Save it as:

   `data/raw/fake_job_postings.csv`

The loader also accepts the legacy filename `DataSet.csv` if you already have a local copy.

## Requirements

- Python 3.10+
- See [requirements.txt](requirements.txt)

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows
pip install -r requirements.txt
python -c "import nltk; nltk.download('stopwords')"
```

## Train

```bash
python scripts/train.py --data-path data/raw/fake_job_postings.csv
```

Artifacts are written to `models/`:

- `vectorizer.joblib`
- `naive_bayes.joblib`
- `decision_tree.joblib`
- `metrics.json`

## Predict (CLI)

```bash
python scripts/predict.py --text "Earn $5000 weekly from home. No experience required!"
```

Or pipe text:

```bash
echo "Software engineer with Python experience." | python scripts/predict.py
```

## Demo app

```bash
streamlit run app/streamlit_app.py
```

## Tests

```bash
pytest
```

## Methodology (summary)

| Step | Description |
|------|-------------|
| Cleaning | Drop high-null / ID columns; fill missing text with spaces |
| Features | Concatenate title, location, company profile, description, requirements, benefits, industry |
| Balance | `RandomUnderSampler` on the training split |
| Vectorization | Bag-of-words (`CountVectorizer`) |
| Models | Multinomial NB and Decision Tree; metrics on held-out test set |

## License

MIT — see [LICENSE](LICENSE).

## Acknowledgments

Original exploratory analysis: [Aakash549/Fake-job-detection-using-machine-learning](https://github.com/Aakash549/Fake-job-detection-using-machine-learning).
