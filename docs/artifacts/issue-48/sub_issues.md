# Issue #48 Sub-Issue Breakdown

This issue is split into atomic, non-overlapping sub-issues.

## Sub-issue A (contract + docs foundation)

- Scope: Define hash-chain receipt integrity and decision-scoped audit export
  contracts.
- Done when:
  - `spec/API.md` documents decision audit export endpoint and payload fields.
  - `spec/EVENT_SCHEMA.md` documents integrity projection fields.
  - `spec/BUSINESS_RULES.md` defines hash-chain integrity rule and failure mode.

## Sub-issue B (store-level integrity chain)

- Scope: Persist deterministic `prev_hash` + `hash` per append-only stored event.
- Boundaries:
  - Keep append-only semantics (no mutable rewrites).
  - Preserve in-memory and sqlite backend behavior parity.

## Sub-issue C (decision-trace export service + endpoint)

- Scope: Add `GET /v1/approvals/decisions/{decision_id}/audit-export`.
- Done when:
  - Full receipt trail is reconstructable for one `decision_id`.
  - Export includes tamper-evident chain fields.

## Sub-issue D (runtime receipt linkage hardening)

- Scope: Persist `approval.decision_id` for runtime receipts when available.
- Done when:
  - Runtime decision/action/error receipts link back to the decision trace.

## Sub-issue E (closure + assessment)

- Scope: Final closure documentation and downstream gap assessment.
- Done when:
  - `docs/artifacts/issue-48/gap_assessment.md` exists.
  - `docs/diary.md` includes implementation and validation evidence.
