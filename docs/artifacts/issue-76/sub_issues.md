# Issue #76 Sub-Issue Breakdown

This issue is split into atomic, non-overlapping sub-issues.

## Sub-issue A (contract + docs foundation)

- Scope: define adoption bootstrap docs and contract versioning policy baseline.
- Done when:
  - `README.md` includes adoption quickstart path.
  - `spec/API.md` defines authorize_action versioning semantics.
  - `docs/artifacts/issue-76/sub_issues.md` exists.

## Sub-issue B (one-command bootstrap path)

- Scope: ship a runnable one-command local bootstrap for API + MCP.
- Done when:
  - A bootstrap script exists and starts both runtime services.
  - README command path matches the script.

## Sub-issue C (client config templates)

- Scope: provide copy-paste MCP client examples for local and remote usage.
- Done when:
  - README includes at least one local stdio and one remote HTTP example.
  - Examples map to current transport headers and protocol version.

## Sub-issue D (contract version markers + locks)

- Scope: expose explicit version marker for authorize_action contract and lock
  it with tests.
- Done when:
  - Tool contract metadata includes explicit contract version marker.
  - Tests lock version marker and compatibility docs.

## Sub-issue E (closure + assessment)

- Scope: final assessment against remaining open issues.
- Done when:
  - `docs/artifacts/issue-76/gap_assessment.md` exists.
  - `docs/diary.md` includes issue summary and validation evidence.
