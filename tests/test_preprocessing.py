from fake_job_detector.preprocessing import (
    build_combined_text,
    drop_unused_columns,
    prepare_dataset,
)


def test_drop_unused_columns(sample_job_frame):
    out = drop_unused_columns(sample_job_frame)
    assert "job_id" not in out.columns
    assert "salary_range" not in out.columns
    assert "title" in out.columns


def test_build_combined_text(sample_job_frame):
    cleaned = drop_unused_columns(sample_job_frame)
    narrow = build_combined_text(cleaned)
    assert list(narrow.columns) == ["text", "fraudulent"]
    assert "python" in narrow["text"].iloc[0].lower()


def test_prepare_dataset_balanced(sample_job_frame):
    texts, labels = prepare_dataset(sample_job_frame, random_state=42)
    assert len(texts) == len(labels)
    assert labels.value_counts().nunique() == 1
