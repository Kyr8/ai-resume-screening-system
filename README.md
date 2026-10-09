# AI Resume Screening & Ranking System

A small, explainable Python CLI that processes a folder of resumes, applies hard Python + AI eligibility checks, ranks eligible candidates, and optionally enriches scores with public GitHub repository activity.

## Requirements

- Python 3.11+
- Internet access only for GitHub enrichment
- PDF resumes must contain selectable text. Scanned/image-only PDFs need OCR, which is outside the first version.

## Setup (Windows PowerShell)

```powershell
cd path\to\ai_resume_screening
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
```

If PowerShell blocks activation, run commands with `.\.venv\Scripts\python.exe` instead.

## Run against the resume folder

Place the supplied resume files in a folder named `resumes` beside `main.py`, then run:

```powershell
python main.py --input .\resumes --output .\output\results.json
```

Skip network calls if you need a quick offline run:

```powershell
python main.py --input .\resumes --output .\output\results.json --no-github
```

Supported inputs: PDF, DOCX, TXT. Unsupported files are ignored. An unreadable resume is recorded as a failure instead of crashing the batch.

## Run tests

```powershell
python -m pytest -q
```

## Optional LLM review

To enable semantic AI-project review, set environment variables in your terminal before running:

```powershell
$env:OPENAI_API_KEY = "your-key"
$env:OPENAI_MODEL = "gpt-4o-mini"
python main.py --input .\\resumes --output .\\output\\results.json
```

Without `OPENAI_API_KEY`, the project still runs using deterministic scoring. When enabled, the LLM only reviews AI-project depth and returns JSON fields for a summary, strengths, concerns, and evidence quotes. The Python + AI hard eligibility gate remains deterministic, and an LLM failure falls back to the heuristic score. Resume text is explicitly treated as untrusted input in the review prompt. API usage may incur cost.

## Output

`output/results.json` contains:
- batch totals: files, parsed, eligible, rejected, failures
- eligible candidates ranked by score
- rejection reasons for ineligible candidates
- matched skills and short resume evidence snippets
- score breakdown for each eligible candidate
- GitHub enrichment status and summary

## Design Decisions

### Eligibility before ranking
Python and meaningful AI/LLM/agentic implementation evidence are hard gates. A strong React/Java profile does not pass without both. A lone AI keyword with little implementation context is treated cautiously. The eligibility checks are deterministic and easy to test.

### Explainable baseline scoring
The score is capped at 100 using the assignment's weights: AI project depth (40), Python/backend (30), cloud/full stack (15), GitHub (10), and engineering depth (5). The first version uses transparent phrase/context heuristics, records evidence snippets, and includes a scoring note. It is a baseline, not a claim that keyword heuristics understand project quality perfectly. Inspect top results and tune against the provided resume set.

### Optional LLM review
The LLM provider is isolated in `resume_screening/llm_review.py`, returns a bounded JSON review, and is optional. The core system does not require an API key. The model can make mistakes, so its score and evidence quotes should be reviewed rather than treated as ground truth.

### GitHub enrichment
For eligible candidates with a GitHub username, the program checks public repositories through the GitHub API. It estimates activity from repositories pushed to in the last 180 days and relevance from repository names/descriptions/topics. It checks at most 30 repositories, uses a timeout, and continues if the API errors. Missing GitHub never makes a candidate ineligible. A `GITHUB_TOKEN` environment variable is optional.

### Reliability
Each file is isolated in exception handling; a malformed resume cannot terminate the batch. Exact duplicate extracted text is detected. No database, frontend, deployment, or vector database is needed for the stated scope.

### Responsible use
This tool is decision support. Resume extraction and heuristic scores can be wrong. Review the cited evidence and do not use protected or irrelevant personal attributes to rank people.

## If I Had More Time

1. Add OCR for image-only PDFs and improve name/section extraction.
2. Add an optional LLM adapter with schema-validated output for project depth, with deterministic eligibility gates and fallbacks.
3. Add caching and bounded concurrency for GitHub calls, with tests for rate limits and failures.
4. Evaluate the scoring rules against a manually reviewed sample and measure false positives/negatives.

## Current limitations

- Heuristic extraction and scoring can miss unusual resume wording or over-credit keyword-heavy resumes.
- GitHub repository metadata is only a proxy for engineering activity; it does not establish authorship or code quality.
- GitHub API activity is based on repository `pushed_at`, not a complete contribution graph.
- Without an API key, the first version uses deterministic scoring and is repeatable. With an API key, AI project-depth scoring becomes model-assisted and may vary by model/provider.
