-- Mart model: one row per repository — issue-health summary.
--
-- avg_days_to_close is computed over closed issues only; open issues
-- would bias it downward (they haven't finished aging yet).
-- top_authors ranks issue authors per repo and concatenates the top 5.

with issues as (

    select * from {{ ref('stg_issues') }}

),

repo_stats as (

    select
        repo,
        count(*)                                          as total_issues,
        count(*) filter (where not is_closed)             as open_issues,
        count(*) filter (where is_closed)                 as closed_issues,
        round(avg(days_open) filter (where is_closed), 1) as avg_days_to_close
    from issues
    group by repo

),

ranked_authors as (

    select
        repo,
        author_login,
        count(*) as issues_opened,
        row_number() over (
            partition by repo
            order by count(*) desc, author_login
        ) as author_rank
    from issues
    where author_login is not null
    group by repo, author_login

),

top_authors as (

    select
        repo,
        string_agg(author_login, ', ' order by author_rank) as top_authors
    from ranked_authors
    where author_rank <= 5
    group by repo

)

select
    r.repo,
    r.total_issues,
    r.open_issues,
    r.closed_issues,
    r.avg_days_to_close,
    a.top_authors
from repo_stats r
left join top_authors a
  on r.repo = a.repo
