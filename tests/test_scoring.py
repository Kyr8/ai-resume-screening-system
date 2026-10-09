from resume_screening.scoring import eligibility, score_candidate

def candidate(text):
    return {"raw_text": text, "matched_skills": []}

def test_python_and_ai_evidence_passes():
    c = candidate("Built a Python FastAPI RAG pipeline using embeddings and vector search.")
    assert eligibility(c)[0] is True

def test_javascript_only_is_rejected():
    c = candidate("Developed a React and JavaScript dashboard with CSS.")
    ok, reasons = eligibility(c)
    assert ok is False
    assert any("Python" in reason for reason in reasons)

def test_python_without_ai_is_rejected():
    c = candidate("Built a Python API with FastAPI and PostgreSQL.")
    assert eligibility(c)[0] is False

def test_score_is_bounded_and_breakdown_present():
    c = candidate("Built a Python FastAPI RAG pipeline using LangChain, Docker, pytest, caching and evaluation.")
    score = score_candidate(c, {"score": 5})
    assert 0 <= score["total_score"] <= 100
    assert sum(score["score_breakdown"].values()) == score["total_score"]
