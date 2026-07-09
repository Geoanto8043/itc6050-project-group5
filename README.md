# ITC6050 Final Project — Group 5: GitHub Open Source Pulse

End-to-end data pipeline that ingests repository statistics and issue
activity from the GitHub REST API and analyses community health, issue
resolution time, and contribution patterns across popular open-source
projects.

**Stack:** dlt (ingestion) → PostgreSQL (storage) → dbt (transformation +
tests) → Streamlit (dashboard).

The default tracked repositories are the open-source tools used to build
this very pipeline: dlt, dbt-core, Streamlit, Airflow, pandas, DuckDB
(configurable via `TRACKED_REPOS` in `.env`).

```
GitHub REST API (/repos, /issues) ─ pipeline.py (dlt) ─→ PostgreSQL: raw schema
                                                               │
                                                               ▼
                                            dbt: stg_issues (view)
                                                 repo_issue_summary (table)
                                                               │
                                                               ▼
                                                   dashboard.py (Streamlit)
```

## Setup

Prerequisites: Python 3.12, Docker (for PostgreSQL 16), a free GitHub
personal access token (Settings → Developer Settings → Personal Access
Tokens → classic token with `public_repo` scope).

```bash
# 1. PostgreSQL
docker run -d --name itc6050_postgres \
  -e POSTGRES_USER=dataeng -e POSTGRES_PASSWORD=dataeng \
  -e POSTGRES_DB=github_pulse -p 5432:5432 postgres:16

# 2. Python environment
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Secrets — paste your GitHub token into .env
cp .env.example .env
```

## Run the pipeline

```bash
# Ingest repos + issues into the raw schema (full refresh, ~20 API calls)
python pipeline.py

# Build staging + mart models and run all data quality tests
cd analytics
dbt run  --profiles-dir .
dbt test --profiles-dir .
cd ..

# Launch the dashboard at http://localhost:8501
streamlit run dashboard.py
```

## Repository structure

```
├── pipeline.py            dlt ingestion (repos + issues, paginated, PR-filtered)
├── dashboard.py           Streamlit dashboard (KPIs, charts, tables, filters)
├── requirements.txt       pinned dependencies
├── .env.example           configuration template (no real keys)
└── analytics/             dbt project
    ├── dbt_project.yml
    ├── profiles.yml       connection profile (reads PG* env vars)
    ├── models/
    │   ├── sources.yml    raw-table declarations + descriptions
    │   ├── schema.yml     model docs + generic tests
    │   ├── stg_issues.sql
    │   └── repo_issue_summary.sql
    └── tests/
        └── assert_issue_unique_per_repo.sql
```

## Data quality

dbt tests cover: `not_null` (issue_id, repo, state, mart keys),
`accepted_values` on state (`open`/`closed`), `unique` on the mart's repo
key, and a custom singular test asserting each issue id appears at most
once per repository.

## Notes

- The GitHub Issues endpoint returns pull requests as well; the extractor
  drops anything carrying a `pull_request` key, so the raw `issues` table
  holds real issues only.
- Ingestion walks pages newest-first (100 per page, 3 pages per repo) to
  keep runs bounded and well inside GitHub's 5,000 req/hour authenticated
  rate limit.
