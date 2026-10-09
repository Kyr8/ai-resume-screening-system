import os
import requests
from datetime import datetime, timezone

API = "https://api.github.com"
TIMEOUT = 5

def enrich_github(username):
    if not username:
        return {"status": "not_found", "score": 0, "summary": "No GitHub profile found in resume."}
    headers = {"Accept": "application/vnd.github+json"}
    token = os.getenv("GITHUB_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    try:
        user_response = requests.get(f"{API}/users/{username}", headers=headers, timeout=TIMEOUT)
        if user_response.status_code == 404:
            return {"status": "not_found", "score": 0, "summary": "GitHub profile not found or unavailable."}
        user_response.raise_for_status()
        repos_response = requests.get(
            f"{API}/users/{username}/repos",
            params={"sort": "updated", "per_page": 30, "type": "owner"},
            headers=headers, timeout=TIMEOUT
        )
        repos_response.raise_for_status()
        repos = repos_response.json()
        public_count = len(repos)
        relevant = [
            r for r in repos
            if any(k in ((r.get("name") or "") + " " + (r.get("description") or "") + " " + " ".join(r.get("topics") or [])).lower()
                   for k in ["python", "ai", "llm", "rag", "agent", "machine-learning", "fastapi"])
        ]
        now = datetime.now(timezone.utc)
        recent = 0
        for repo in repos:
            updated = repo.get("pushed_at")
            if updated:
                try:
                    dt = datetime.fromisoformat(updated.replace("Z", "+00:00"))
                    if (now - dt).days <= 180:
                        recent += 1
                except ValueError:
                    pass
        activity_points = min(5, recent)
        repo_points = min(5, len(relevant))
        score = activity_points + repo_points
        summary = f"{recent} repositories pushed to in the last 180 days; {len(relevant)} recent public repositories appear Python/AI-relevant (up to 30 checked)."
        return {
            "status": "success", "score": score, "summary": summary,
            "public_repositories_checked": public_count,
            "recently_active_repositories": recent,
            "relevant_repositories": len(relevant),
        }
    except requests.RequestException as exc:
        return {"status": "error", "score": 0, "summary": f"GitHub enrichment failed; screening continued ({type(exc).__name__})."}
