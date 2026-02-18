# Issue #44 Sub-Issue Breakdown

This issue is split into atomic, non-overlapping sub-issues so we can ship and verify incrementally.

## Sub-issue 1 (active in this branch)

- Scope: Introduce the transport contract surface for `authorize_action(intent, context)` with deterministic `decision_id` generation and structured request validation errors.
- Boundaries:
  - Supports only `intent.action = "purchase.create"` for the initial contract surface.
  - Does not implement policy-threshold governance logic from issue #45.
- Done when:
  - API contract docs define request and response envelopes.
  - Automated tests verify deterministic `decision_id` and structured invalid-payload errors.
  - Endpoint is callable and returns a contract-compliant response for valid payloads.

## Sub-issue 2 (deferred)

- Scope: Expand decision-state coverage to guarantee all v1 decision states (`allow`, `requires_approval`, `deny`) are produced via deterministic contract rules.
- Boundaries:
  - No human approval transition orchestration (issue #46).
  - No runtime executor token enforcement (issue #47).

## Sub-issue 3 (deferred)

- Scope: README operator/client examples and end-to-end smoke path for agent-client invocation.
- Boundaries:
  - No append-only receipt integrity expansion (issue #48).
  - No full demo orchestration packaging (issue #49).
