
from pathlib import Path
from .parser import extract_text, parse_candidate, list_resume_files
from .scoring import eligibility, score_candidate
from .github_enrichment import enrich_github as fetch_github_profile
from .llm_review import review_project_with_llm


def screen_directory(input_dir: Path, enrich_github: bool = True) -> dict:
    input_dir = Path(input_dir)

    if not input_dir.exists() or not input_dir.is_dir():
        raise ValueError(
            f"Input directory does not exist or is not a directory: {input_dir}"
        )

    files = list_resume_files(input_dir)
    results = []
    failures = []
    seen_hashes = set()

    import hashlib

    for path in files:
        try:
            raw = extract_text(path)

            digest = hashlib.sha256(
                raw.encode("utf-8", errors="replace")
            ).hexdigest()

            if digest in seen_hashes:
                results.append({
                    "candidate_name": path.stem,
                    "source_file": path.name,
                    "eligible": False,
                    "rejection_reasons": [
                        "Duplicate resume content detected"
                    ],
                    "matched_skills": [],
                    "total_score": 0,
                    "github": {
                        "status": "skipped",
                        "score": 0,
                        "summary": "Duplicate content."
                    }
                })
                continue

            seen_hashes.add(digest)

            candidate = parse_candidate(path, raw)
            eligible, reasons = eligibility(candidate)

            result = {
                "candidate_name": candidate["candidate_name"],
                "source_file": candidate["source_file"],
                "email": candidate["email"],
                "github_username": candidate["github_username"],
                "eligible": eligible,
                "rejection_reasons": reasons,
                "matched_skills": candidate["matched_skills"],
            }

            if eligible:
                github = (
                    fetch_github_profile(candidate["github_username"])
                    if enrich_github
                    else {
                        "status": "skipped",
                        "score": 0,
                        "summary": "GitHub enrichment disabled."
                    }
                )

                scores = score_candidate(candidate, github)
                llm_review = review_project_with_llm(
                    candidate["raw_text"]
                )

                if llm_review and llm_review.get("status") == "success":
                    scores["score_breakdown"]["ai_project_depth"] = (
                        llm_review["ai_project_depth_score"]
                    )
                    scores["total_score"] = sum(
                        scores["score_breakdown"].values()
                    )
                    scores["scoring_note"] = (
                        "AI project depth reviewed by optional LLM; "
                        "other categories use deterministic heuristics. "
                        "Verify evidence."
                    )
                    result["llm_review"] = llm_review

                elif llm_review:
                    result["llm_review"] = llm_review

                else:
                    result["llm_review"] = {
                        "status": "not_configured",
                        "summary": (
                            "Set OPENAI_API_KEY to enable semantic project "
                            "review; deterministic scoring used."
                        )
                    }

                result.update(scores)
                result["github"] = github

            else:
                result["total_score"] = 0
                result["github"] = {
                    "status": "skipped",
                    "score": 0,
                    "summary": "Ineligible candidates are not enriched."
                }

            results.append(result)

        except Exception as exc:
            failures.append({
                "source_file": path.name,
                "error": (
                    f"{type(exc).__name__}: {str(exc)[:240]}"
                )
            })

    eligible_results = [
        result for result in results
        if result.get("eligible")
    ]

    eligible_results.sort(
        key=lambda result: (
            -result.get("total_score", 0),
            result.get("candidate_name", "").lower()
        )
    )

    for rank, result in enumerate(eligible_results, 1):
        result["rank"] = rank

    rejected = [
        result for result in results
        if not result.get("eligible")
    ]

    final_candidates = eligible_results + rejected

    return {
        "metadata": {
            "scoring_version": "1.0",
            "input_directory": str(input_dir),
            "github_enrichment_enabled": enrich_github,
            "note": (
                "Automated screening is decision support, not a final "
                "hiring decision. Validate evidence and avoid using "
                "protected or irrelevant personal attributes."
            )
        },
        "batch_summary": {
            "total_resumes": len(files),
            "successfully_parsed": len(files) - len(failures),
            "eligible": len(eligible_results),
            "rejected": len(rejected),
            "failed_unreadable": len(failures),
        },
        "candidates": final_candidates,
        "failures": failures,
    }
