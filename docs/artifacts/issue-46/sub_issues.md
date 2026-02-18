# Issue #46 Sub-Issue Breakdown

This issue is split into atomic, non-overlapping sub-issues to deliver
decision-id approval flow without breaking existing event-id approval callers.

## Sub-issue A (contract + schema foundation)

- Scope: Define decision-id approval contract in docs and schema.
- Boundaries:
  - Keep existing `POST /v1/approvals/{event_id}` as legacy compatibility.
  - No executor token verification (issue #47).
  - No tamper-evident hash chaining work (issue #48).
- Done when:
  - `spec/API.md` documents register/resolve/query by `decision_id`.
  - `spec/EVENT_SCHEMA.md` includes optional `approval.decision_id`.
  - Doc-lock tests enforce new contract language.

## Sub-issue B (decision approval services)

- Scope: Add governance/service support for decision-id registration, resolution,
  and lookup.
- Boundaries:
  - Append-only receipts only; no direct mutable approval tables.
  - Preserve existing event-id resolution behavior.
- Done when:
  - Pending approval can be registered from `decision_id`.
  - Decision approval can transition once (`pending -> approved|rejected`).
  - Duplicate/late submissions fail loudly with structured errors.

## Sub-issue C (HTTP wiring + compatibility)

- Scope: Introduce new endpoints:
  - `POST /v1/approvals/requests`
  - `POST /v1/approvals/decisions/{decision_id}`
  - `GET /v1/approvals/decisions/{decision_id}`
- Boundaries:
  - Legacy `POST /v1/approvals/{event_id}` remains supported.
  - No UI coupling in governance logic.
- Done when:
  - New endpoints are live and tested.
  - Legacy route behavior remains green in existing tests.
  - Error envelopes stay deterministic and structured.

## Sub-issue D (operator docs + audit closure)

- Scope: Human-readable closure outputs for issue #46 and downstream gap
  analysis.
- Done when:
  - README flow includes decision-id approval path.
  - `docs/artifacts/issue-46/gap_assessment.md` records post-implementation
    assessment against open issues (#47/#48/#49).
  - `docs/diary.md` includes issue completion summary and validation evidence.
