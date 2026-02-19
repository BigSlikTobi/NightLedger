# Progress Update Issue-Link Policy

Date: 2026-02-19

Parent issue: #62

Implementation track: SI-62A (#88)

## Rule

All tracked progress artifacts must include at least one valid numeric GitHub
issue reference in `#<number>` form.

Rejected placeholders:

- `#unknown`
- `#TBD`

## Tracked Progress Artifacts

- `docs/diary.md`
- `docs/artifacts/**.md`

## Enforcement

- CI job: `validate-progress-refs`
- Command:

```bash
bash tasks/validate_progress_issue_links.sh
```

## Notes

This policy is process-only and does not change runtime API behavior.
