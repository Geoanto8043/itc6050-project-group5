-- Custom singular test (required by the brief):
-- an issue id must appear at most once per repository.
-- GitHub issue ids are globally unique, so a duplicate (issue_id, repo)
-- pair can only mean the extractor loaded a page twice.
-- Returns offending pairs; the test passes when no rows come back.

select
    repo,
    issue_id,
    count(*) as occurrences
from {{ ref('stg_issues') }}
group by repo, issue_id
having count(*) > 1
