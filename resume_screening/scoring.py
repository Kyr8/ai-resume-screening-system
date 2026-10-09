import re

PYTHON_EVIDENCE = [
    r"\bpython\b", r"\bfastapi\b", r"\bdjango\b", r"\bflask\b", r"\bpython\s+(?:backend|service|script|application)\b"
]
AI_EVIDENCE = [
    r"\blangchain\b", r"\blanggraph\b", r"\bllamaindex\b", r"\brag\b",
    r"retrieval[- ]augmented generation", r"\bvector search\b", r"\bembeddings?\b",
    r"\btool[- ]calling\b", r"\b(?:multi[- ]?)?agent(?:ic)?\b", r"\bllm\b",
    r"\bopenai\b", r"\btransformers\b", r"\bsemantic search\b", r"\bai assistant\b"
]
PROJECT_CUES = [
    "built", "implemented", "developed", "designed", "deployed", "pipeline",
    "workflow", "retrieval", "vector", "evaluation", "orchestration", "api",
    "database", "state", "tool calling", "agent"
]
SHALLOW_CUES = [
    "simple chatbot", "basic chatbot", "just an api call", "tutorial project",
    "followed a tutorial", "wrapper around", "prompt wrapper"
]

def _has(patterns, text):
    return any(re.search(p, text, re.I) for p in patterns)

def eligibility(candidate):
    text = candidate["raw_text"]
    lower = text.lower()
    python_ok = _has(PYTHON_EVIDENCE, text)
    ai_ok = _has(AI_EVIDENCE, text)
    reasons = []
    if not python_ok:
        reasons.append("No clear Python skill, project, or work evidence")
    if not ai_ok:
        reasons.append("No meaningful AI/LLM/agentic evidence detected")
    # AI evidence must have some contextual evidence beyond an isolated keyword.
    ai_terms = sum(1 for p in AI_EVIDENCE if re.search(p, text, re.I))
    project_context = sum(1 for cue in PROJECT_CUES if cue in lower)
    if ai_ok and ai_terms == 1 and project_context < 2:
        ai_ok = False
        reasons.append("AI evidence appears keyword-only; no clear project/implementation context")
    return python_ok and ai_ok, reasons

def score_candidate(candidate, github):
    text = candidate["raw_text"]
    lower = text.lower()
    # Transparent heuristic scoring. Evidence is retained so a reviewer can challenge it.
    ai_hits = sum(1 for cue in [
        "rag", "retrieval", "embeddings", "vector search", "langchain", "langgraph",
        "tool calling", "multi-agent", "orchestration", "evaluation", "stateful",
        "llamaindex", "semantic search"
    ] if cue in lower)
    ai_project_context = sum(1 for cue in ["built", "implemented", "developed", "pipeline", "workflow", "deployed"] if cue in lower)
    ai = min(40, ai_hits * 4 + ai_project_context * 3)
    if any(cue in lower for cue in SHALLOW_CUES):
        ai = max(0, ai - 10)

    python_hits = sum(1 for cue in ["python", "fastapi", "django", "flask", "async", "postgres", "redis", "sqlalchemy", "pytest"] if cue in lower)
    backend_context = sum(1 for cue in ["api", "backend", "database", "endpoint", "authentication", "testing", "schema"] if cue in lower)
    backend = min(30, python_hits * 2 + backend_context * 2)

    cloud_hits = sum(1 for cue in ["docker", "gcp", "google cloud", "aws", "azure", "deploy", "react", "next.js", "frontend"] if cue in lower)
    cloud = min(15, cloud_hits * 2)

    engineering_hits = sum(1 for cue in [
        "unit test", "pytest", "caching", "cache", "observability", "logging",
        "retry", "rate limit", "concurrency", "async", "queue", "architecture",
        "monitoring", "error handling"
    ] if cue in lower)
    engineering = min(5, engineering_hits)

    github_score = int(github.get("score", 0)) if github else 0
    github_score = max(0, min(10, github_score))
    total = min(100, ai + backend + cloud + github_score + engineering)

    # Brief evidence snippets: small, auditable excerpts around relevant terms.
    evidence = []
    for term in ["python", "rag", "langchain", "langgraph", "fastapi", "docker", "evaluation", "vector"]:
        match = re.search(term, text, re.I)
        if match:
            start, end = max(0, match.start() - 65), min(len(text), match.end() + 100)
            snippet = re.sub(r"\s+", " ", text[start:end]).strip()
            if snippet and snippet not in evidence:
                evidence.append(snippet)
        if len(evidence) >= 5:
            break

    return {
        "total_score": total,
        "score_breakdown": {
            "ai_project_depth": ai,
            "python_backend": backend,
            "cloud_fullstack": cloud,
            "github": github_score,
            "engineering_depth": engineering,
        },
        "evidence": evidence,
        "scoring_note": "Deterministic heuristic score; review evidence before making a hiring decision."
    }
