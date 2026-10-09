import pytest
from resume_screening import pipeline


def test_invalid_input_directory_raises_error(tmp_path):
    missing = tmp_path / "missing"

    with pytest.raises(ValueError, match="Input directory"):
        pipeline.screen_directory(missing)


def test_duplicate_resume_content_is_rejected(tmp_path, monkeypatch):
    resume_dir = tmp_path / "resumes"
    resume_dir.mkdir()

    content = "Built a Python FastAPI RAG pipeline using embeddings and vector search."
    (resume_dir / "first.txt").write_text(content)
    (resume_dir / "second.txt").write_text(content)

    monkeypatch.setattr(
        pipeline,
        "fetch_github_profile",
        lambda username: {"status": "skipped", "score": 0, "summary": "Test"},
    )
    monkeypatch.setattr(pipeline, "review_project_with_llm", lambda text: None)

    result = pipeline.screen_directory(resume_dir, enrich_github=True)

    duplicates = [
        candidate
        for candidate in result["candidates"]
        if "Duplicate resume content detected"
        in candidate.get("rejection_reasons", [])
    ]

    assert len(duplicates) == 1
    assert result["batch_summary"]["total_resumes"] == 2
    assert result["batch_summary"]["rejected"] >= 1


def test_one_bad_resume_does_not_stop_batch(tmp_path, monkeypatch):
    resume_dir = tmp_path / "resumes"
    resume_dir.mkdir()

    (resume_dir / "good.txt").write_text(
        "Built a Python FastAPI RAG pipeline using embeddings and vector search."
    )
    (resume_dir / "bad.txt").write_text("This file will fail during extraction.")

    original_extract = pipeline.extract_text

    def extract_with_one_failure(path):
        if path.name == "bad.txt":
            raise OSError("Simulated unreadable resume")
        return original_extract(path)

    monkeypatch.setattr(pipeline, "extract_text", extract_with_one_failure)
    monkeypatch.setattr(
        pipeline,
        "fetch_github_profile",
        lambda username: {"status": "skipped", "score": 0, "summary": "Test"},
    )
    monkeypatch.setattr(pipeline, "review_project_with_llm", lambda text: None)

    result = pipeline.screen_directory(resume_dir)

    assert result["batch_summary"]["total_resumes"] == 2
    assert result["batch_summary"]["failed_unreadable"] == 1
    assert len(result["failures"]) == 1
    assert result["failures"][0]["source_file"] == "bad.txt"
    assert len(result["candidates"]) == 1


def test_github_failure_does_not_stop_screening(tmp_path, monkeypatch):
    resume_dir = tmp_path / "resumes"
    resume_dir.mkdir()

    (resume_dir / "candidate.txt").write_text(
        "Built a Python FastAPI RAG pipeline using embeddings and vector search."
    )

    monkeypatch.setattr(
        pipeline,
        "fetch_github_profile",
        lambda username: {
            "status": "error",
            "score": 0,
            "summary": "Simulated GitHub failure",
        },
    )
    monkeypatch.setattr(pipeline, "review_project_with_llm", lambda text: None)

    result = pipeline.screen_directory(resume_dir)

    assert result["batch_summary"]["total_resumes"] == 1
    assert result["batch_summary"]["failed_unreadable"] == 0
    assert result["candidates"][0]["eligible"] is True
    assert result["candidates"][0]["github"]["status"] == "error"


def test_llm_failure_preserves_deterministic_score(tmp_path, monkeypatch):
    resume_dir = tmp_path / "resumes"
    resume_dir.mkdir()

    (resume_dir / "candidate.txt").write_text(
        "Built a Python FastAPI RAG pipeline using embeddings and vector search."
    )

    monkeypatch.setattr(
        pipeline,
        "fetch_github_profile",
        lambda username: {"status": "success", "score": 3, "summary": "Test"},
    )
    monkeypatch.setattr(
        pipeline,
        "review_project_with_llm",
        lambda text: {
            "provider": "openai",
            "status": "error",
            "error": "Simulated LLM failure",
        },
    )

    result = pipeline.screen_directory(resume_dir)
    candidate = result["candidates"][0]

    assert candidate["eligible"] is True
    assert candidate["total_score"] > 0
    assert candidate["llm_review"]["status"] == "error"
    assert result["batch_summary"]["failed_unreadable"] == 0
