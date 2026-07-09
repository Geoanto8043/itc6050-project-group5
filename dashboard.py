"""ITC6050 Final Project — Group 5: GitHub Open Source Pulse dashboard.

Reads the dbt models (analytics.stg_issues, analytics.repo_issue_summary)
from PostgreSQL and presents issue activity and community health across
the tracked open-source repositories.

Run:  streamlit run dashboard.py
"""

import os

import pandas as pd
import plotly.express as px
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine

load_dotenv()

# Categorical palette, fixed slot order (slot 1 blue, slot 2 aqua):
# open vs closed is a two-series comparison, so each state keeps its
# colour everywhere. Single-measure charts use blue alone.
BLUE = "#2a78d6"
AQUA = "#1baf7a"
STATE_COLORS = {"open": BLUE, "closed": AQUA}

st.set_page_config(
    page_title="GitHub Open Source Pulse — ITC6050 Group 5",
    layout="wide",
)


@st.cache_data(ttl=600)
def load_tables() -> tuple[pd.DataFrame, pd.DataFrame]:
    engine = create_engine(
        f"postgresql+psycopg2://{os.getenv('PGUSER', 'dataeng')}:"
        f"{os.getenv('PGPASSWORD', 'dataeng')}@"
        f"{os.getenv('PGHOST', 'localhost')}:{os.getenv('PGPORT', '5432')}/"
        f"{os.getenv('PGDATABASE', 'github_pulse')}"
    )
    issues = pd.read_sql(
        "select repo, state, is_closed, author_login, created_at, "
        "closed_at, days_open from analytics.stg_issues",
        engine,
        parse_dates=["created_at", "closed_at"],
    )
    summary = pd.read_sql(
        "select * from analytics.repo_issue_summary order by total_issues desc",
        engine,
    )
    return issues, summary


issues, summary = load_tables()

st.title("GitHub Open Source Pulse")
st.caption(
    "Issue activity and community health for the open-source tools behind "
    "this very pipeline — GitHub REST API, via dlt → PostgreSQL → dbt"
)

# ---------------------------------------------------------------- filters --
f1, f2, f3 = st.columns([2, 1, 2])
with f1:
    repos = sorted(issues["repo"].unique())
    selected_repos = st.multiselect("Repository", repos, default=repos)
with f2:
    selected_states = st.multiselect(
        "State", ["open", "closed"], default=["open", "closed"]
    )
with f3:
    min_date = issues["created_at"].min().date()
    max_date = issues["created_at"].max().date()
    date_range = st.date_input(
        "Created between",
        value=(min_date, max_date),
        min_value=min_date,
        max_value=max_date,
    )

start, end = (date_range if len(date_range) == 2 else (min_date, max_date))
filtered = issues[
    issues["repo"].isin(selected_repos)
    & issues["state"].isin(selected_states)
    & (issues["created_at"].dt.date >= start)
    & (issues["created_at"].dt.date <= end)
]

# -------------------------------------------------------------------- KPIs --
closed = filtered[filtered["is_closed"]]
k1, k2, k3 = st.columns(3)
k1.metric("Repositories tracked", f"{filtered['repo'].nunique()}")
k2.metric("Issues loaded", f"{len(filtered):,}")
k3.metric(
    "Avg days to close",
    f"{closed['days_open'].mean():.1f}" if not closed.empty else "—",
)

st.divider()

# ------------------------------------------------------------------ charts --
left, right = st.columns(2)

with left:
    st.subheader("Issues open vs closed, per repository")
    by_state = (
        filtered.groupby(["repo", "state"], as_index=False)
        .size()
        .rename(columns={"size": "issues"})
    )
    fig = px.bar(
        by_state,
        x="issues",
        y="repo",
        color="state",
        orientation="h",
        barmode="group",
        color_discrete_map=STATE_COLORS,
        category_orders={"state": ["open", "closed"]},
        labels={"issues": "Issues", "repo": "", "state": "State"},
    )
    fig.update_layout(
        margin=dict(l=0, r=0, t=10, b=0),
        height=420,
        legend=dict(orientation="h", y=1.08),
    )
    st.plotly_chart(fig, use_container_width=True)

with right:
    st.subheader("Issues opened per week")
    weekly = (
        filtered.set_index("created_at")
        .resample("W")
        .size()
        .rename("issues")
        .reset_index()
    )
    fig = px.line(
        weekly,
        x="created_at",
        y="issues",
        labels={"created_at": "", "issues": "Issues opened"},
    )
    fig.update_traces(line_color=BLUE, line_width=2)
    fig.update_layout(margin=dict(l=0, r=0, t=10, b=0), height=420)
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------ tables --
t_left, t_right = st.columns(2)

with t_left:
    st.subheader("Top contributors by issues opened")
    contributors = (
        filtered.dropna(subset=["author_login"])
        .groupby(["repo", "author_login"], as_index=False)
        .size()
        .rename(columns={"size": "issues_opened"})
        .sort_values("issues_opened", ascending=False)
        .head(10)
        .reset_index(drop=True)
    )
    st.dataframe(contributors, use_container_width=True)

with t_right:
    st.subheader("Repository summary (dbt mart)")
    st.dataframe(
        summary[summary["repo"].isin(selected_repos)].reset_index(drop=True),
        use_container_width=True,
    )
