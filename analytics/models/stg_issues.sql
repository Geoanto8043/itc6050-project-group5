-- Staging model: one clean row per issue.
--
-- Transformations (documented in report section 5):
--   1. Cast created_at / closed_at from ISO strings to timestamps.
--   2. is_closed — boolean flag derived from state.
--   3. days_open — closed issues: created -> closed; open issues:
--      created -> now. Kept as numeric days with one decimal.
--   4. Drop rows with a null id, repo, or state (defensive; the API
--      guarantees them, but the mart's grain depends on all three).

with source as (

    select
        id                                as issue_id,
        repo,
        number                            as issue_number,
        title,
        state,
        author_login,
        created_at::timestamptz           as created_at,
        closed_at::timestamptz            as closed_at,
        comments,
        loaded_at::timestamptz            as loaded_at
    from {{ source('raw', 'issues') }}
    where id is not null
      and repo is not null
      and state is not null

)

select
    issue_id,
    repo,
    issue_number,
    title,
    state,
    (state = 'closed')                    as is_closed,
    author_login,
    created_at,
    closed_at,
    round(
        extract(
            epoch from coalesce(closed_at, now()) - created_at
        )::numeric / 86400, 1
    )                                     as days_open,
    comments,
    loaded_at
from source
