# Issue #47 Sub-Issue Breakdown

This issue is split into atomic, non-overlapping sub-issues.

## Sub-issue A (contract + docs foundation)

- Scope: Define execution token and protected executor API surfaces in docs.
- Boundary: Enforcement token verification only.
- Done when:
  - `spec/API.md` includes token minting and executor endpoint sections.
  - `README.md` explains trust-boundary verification.

## Sub-issue B (token service)

- Scope: HMAC signing + verification + expiry + action binding.
- Boundaries:
  - No approval-state mutation redesign.
  - No tamper-evident hash chain work (issue #48).

## Sub-issue C (protected executor)

- Scope: Add `POST /v1/executors/purchase.create` guarded by token verification.
- Done when:
  - Missing/invalid/expired/replayed/tampered tokens fail loudly.
  - Valid token allows execution.

## Sub-issue D (approval integration)

- Scope: Add `POST /v1/approvals/decisions/{decision_id}/execution-token`.
- Done when:
  - Token is minted only for approved decisions.
  - Pending/rejected decisions hard-fail with structured errors.

## Sub-issue E (closure + assessment)

- Scope: Final issue closure artifacts and downstream gap assessment.
- Done when:
  - `docs/artifacts/issue-47/gap_assessment.md` exists.
  - `docs/diary.md` records completion and validation evidence.
