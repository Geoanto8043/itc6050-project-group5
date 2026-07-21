# ITC6050 Final Project — Group 5: GitHub Open Source Pulse

This project builds an end-to-end data pipeline that collects data from the GitHub REST API, stores it in PostgreSQL, transforms it using dbt, and analyzes open-source repository activity, issue trends, and project health.

By default, the pipeline collects data from the following open-source repositories:
- dlt
- dbt-core
- Streamlit
- Apache Airflow
- pandas
- DuckDB

The list of repositories can be customized using the `TRACKED_REPOS` variable in `.env`.

## Pipeline Architecture

1. Data Source: GitHub REST API
   - Collects repository statistics and issue activity from GitHub

2. Ingestion: dlt
   - Extracts GitHub data and loads it into PostgreSQL.

3. Storage — PostgreSQL
   - Raw GitHub data is stored in the `raw` schema.
   - Tables include:
     - `repos`
     - `issues`

4. Transformation & Testing — dbt
   - Transforms raw GitHub data into analytics-ready models
   - Creates:
     - `stg_issues`
     - `repo_issue_summary`
   - Runs data quality tests to validate models

5. Visualization — Streamlit
   - Displays interactive dashboard

## Setup

Prerequisites: 
- Python 3.12
- Docker (for PostgreSQL 16)
- GitHub Personal Access Token with `public_repo` scope
  - To create a token:
      - Settings → Developer Settings → Personal Access Tokens → Generate classic token

### 1. Start PostgreSQL with Docker

Create a local PostgreSQL container:

```bash
docker run -d --name itc6050_postgres \
  -e POSTGRES_USER=dataeng \
  -e POSTGRES_PASSWORD=dataeng \
  -e POSTGRES_DB=github_pulse \
  -p 5432:5432 \
  postgres:16
```

### 2. Set up Python environment

Ensure Python 3.12 is installed (other versions may produce errors with `dlt`).

**For macOS/Linux**

```bash
python3.12 -m venv .venv
source .venv/bin/activate

# Ensure latest pip
python -m pip install --upgrade pip
pip install -r requirements.txt
```

**For Windows**

```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate

# Ensure latest pip
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Configure GitHub token

Create `.env` file from the example:

**For macOS/Linux**

```bash
cp .env.example .env
```

**For Windows**

```powershell
Copy-Item .env.example .env
```

Paste GitHub personal access token into the `GITHUB_TOKEN` field in the `.env` file.

### 4. Run the pipeline

Run data ingestion pipeline:

```bash
python pipeline.py
```

Build dbt models and run the tests:

```bash
cd analytics
dbt run --profiles-dir .
dbt test --profiles-dir .
```

Launch Streamlit dashboard:

```bash
cd ..
streamlit run dashboard.py
```

## Repository structure
```text
├── pipeline.py            dlt ingestion
├── dashboard.py           Streamlit dashboard
├── requirements.txt       Virtual environment setup
├── .env.example           Github key and Postgres credentials
└── analytics/             dbt 
    ├── dbt_project.yml
    ├── profiles.yml       Database connection settings
    ├── models/
    │   ├── sources.yml    Defines the raw source tables used by dbt
    │   ├── schema.yml     Defines model documentation and data quality tests
    │   ├── stg_issues.sql
    │   └── repo_issue_summary.sql
    └── tests/
        └── assert_issue_unique_per_repo.sql
```
## Data quality

The project includes automated dbt tests to verify that:

- Required fields are not missing (such as issue IDs, repository names, and issue states)
- Issue states contain only valid values (`open` or `closed`)
- Each repository appears only once in the summary table
- Each issue ID is unique within its repository

## Notes

- GitHub's Issues API also returns pull requests. The pipeline automatically filters these out so only issues are stored in the database.
- To keep pipeline runs fast and within GitHub's API rate limits, the pipeline retrieves only the most recent issues for each repository.
