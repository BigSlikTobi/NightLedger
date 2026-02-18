# Issue #45 Sub-Issue Breakdown

This issue is split into atomic, non-overlapping sub-issues so policy behavior
can ship incrementally without crossing #46/#47/#48/#49 boundaries.

## Sub-issue 1 (completed in this branch)

- Scope: Implement policy-first threshold decisioning for
  `authorize_action(intent, context)` using strict policy inputs and a
  configurable EUR threshold.
- Boundaries:
  - Keeps request-shape compatibility by accepting
    `context.transport_decision_hint` but does not use it to drive final state.
  - Does not add approval transition APIs from issue #46.
  - Does not add executor token verification from issue #47.
- Done when:
  - `context.amount` and `context.currency` are required in policy evaluation.
  - `amount <= threshold` resolves to `allow`.
  - `amount > threshold` resolves to `requires_approval` with
    `reason_code=AMOUNT_ABOVE_THRESHOLD`.
  - Threshold default is `100` EUR and can be overridden by environment config.

## Sub-issue 2 (completed in this branch)

- Scope: Harden operator docs and contract-lock coverage for the updated policy
  input contract across API and README.
- Boundaries:
  - No new policy primitives beyond amount-threshold.
  - No transport-layer redesign.
- Done when:
  - API examples include policy-input validation envelopes.
  - README includes a request-driven operator flow for threshold testing.
  - Contract-lock tests enforce policy docs in API + README + artifact docs.

## Sub-issue 3 (completed in this branch)

- Scope: Cross-issue handoff hardening for downstream work in #46/#47/#49.
- Boundaries:
  - No implementation of decision_id approval resolution.
  - No token-gated purchase executor implementation.
  - No demo orchestration packaging changes.
- Done when:
  - A downstream handoff document maps #45 outcomes to #46/#47/#49 ownership.
  - Out-of-scope boundaries are explicitly documented to prevent overlap.
