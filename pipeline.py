"""ITC6050 Final Project — Group 5: GitHub Open Source Pulse.

Ingestion layer. Extracts repository statistics and issue activity from the
GitHub REST API and loads them into PostgreSQL (schema: raw) using dlt.

Sources:
  1. repos  — one snapshot row per tracked repository.
  2. issues — recent issues per repository, paginated 100 per request.
              Pull requests are excluded (the Issues API returns both).

Run:  python pipeline.py
"""

import os
import sys
from datetime import datetime, timezone

import dlt
import requests
from dotenv import load_dotenv

load_dotenv()

API_BASE = "https://api.github.com"

# The GitHub Issues API serves at most 100 items per page; we walk pages
# newest-first and stop after MAX_ISSUE_PAGES to keep each run bounded
# (6 repos x 3 pages = ~18 requests, well inside the 5,000/hour limit).
PER_PAGE = 100
MAX_ISSUE_PAGES = 3
REQUEST_TIMEOUT = 30

DEFAULT_REPOS = (
    "dlt-hub/dlt,dbt-labs/dbt-core,streamlit/streamlit,"
    "apache/airflow,pandas-dev/pandas,duckdb/duckdb"
)


def tracked_repos() -> list[str]:
    return [
        r.strip()
        for r in os.getenv("TRACKED_REPOS", DEFAULT_REPOS).split(",")
        if r.strip()
    ]


def _headers() -> dict:
    token = os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError(
            "GITHUB_TOKEN is not set. Copy .env.example to .env and paste a "
            "GitHub personal access token (public_repo scope)."
        )
    return {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }


def _get_json(url: str, params: dict | None = None):
    response = requests.get(
        url, params=params, headers=_headers(), timeout=REQUEST_TIMEOUT
    )
    response.raise_for_status()
    return response.json()


@dlt.resource(name="repos", write_disposition="replace")
def repos_resource():
    """One snapshot row per tracked repository."""
    loaded_at = datetime.now(timezone.utc).isoformat()
    for full_name in tracked_repos():
        repo = _get_json(f"{API_BASE}/repos/{full_name}")
        yield {
            "id": repo["id"],
            "name": repo["name"],
            "full_name": repo["full_name"],
            "stars": repo["stargazers_count"],
            "forks": repo["forks_count"],
            "language": repo["language"],
            "open_issues_count": repo["open_issues_count"],
            "created_at": repo["created_at"],
            "loaded_at": loaded_at,
        }


@dlt.resource(name="issues", write_disposition="replace")
def issues_resource():
    """Recent issues for every tracked repo, newest first, paginated.

    The Issues endpoint also returns pull requests; rows carrying a
    'pull_request' key are skipped so the raw table holds issues only.
    """
    loaded_at = datetime.now(timezone.utc).isoformat()
    for full_name in tracked_repos():
        for page in range(1, MAX_ISSUE_PAGES + 1):
            batch = _get_json(
                f"{API_BASE}/repos/{full_name}/issues",
                params={
                    "state": "all",
                    "per_page": PER_PAGE,
                    "page": page,
                    "sort": "created",
                    "direction": "desc",
                },
            )
            if not batch:
                break
            for issue in batch:
                if "pull_request" in issue:
                    continue
                yield {
                    "id": issue["id"],
                    "repo": full_name,
                    "number": issue["number"],
                    "title": issue["title"],
                    "state": issue["state"],
                    "author_login": (issue.get("user") or {}).get("login"),
                    "created_at": issue["created_at"],
                    "closed_at": issue["closed_at"],
                    "labels": [label["name"] for label in issue["labels"]],
                    "comments": issue["comments"],
                    "loaded_at": loaded_at,
                }


@dlt.source(name="github_pulse")
def github_pulse_source():
    return [repos_resource(), issues_resource()]


def build_pipeline() -> dlt.Pipeline:
    credentials = (
        f"postgresql://{os.getenv('PGUSER', 'dataeng')}:"
        f"{os.getenv('PGPASSWORD', 'dataeng')}@"
        f"{os.getenv('PGHOST', 'localhost')}:{os.getenv('PGPORT', '5432')}/"
        f"{os.getenv('PGDATABASE', 'github_pulse')}"
    )
    return dlt.pipeline(
        pipeline_name="github_pulse",
        destination=dlt.destinations.postgres(credentials=credentials),
        dataset_name="raw",
    )


if __name__ == "__main__":
    pipeline = build_pipeline()
    info = pipeline.run(github_pulse_source())
    print(info)
    print(pipeline.last_trace.last_normalize_info)
    sys.exit(0)
