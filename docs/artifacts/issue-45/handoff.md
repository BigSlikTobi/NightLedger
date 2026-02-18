# Issue #45 Downstream Handoff

This handoff defines what issue #45 now guarantees and what remains owned by
downstream runtime issues.

## Scenario Linkage

- `120 EUR -> requires_approval`
  - Produced by `POST /v1/mcp/authorize_action` when
    `context.amount > threshold`.
  - Returns `state=requires_approval` and `reason_code=AMOUNT_ABOVE_THRESHOLD`.
- `80 EUR -> allow`
  - Produced by `POST /v1/mcp/authorize_action` when
    `context.amount <= threshold`.
  - Returns `state=allow` and `reason_code=POLICY_ALLOW_WITHIN_THRESHOLD`.

## Downstream Ownership

| Issue | Ownership after #45 |
| --- | --- |
| #46 | Map policy decisions to decision_id-centered approval transitions and query surfaces. |
| #47 | Enforce token-gated executor boundary so allow/approved decisions are required to execute. |
| #49 | Build deterministic demo script proving purchase flow (block/approve/execute) using #45 outcomes. |

## Out of Scope in #45

- no decision_id approval resolution API
- no executor token verification
- no purchase demo orchestration script packaging
- no new policy primitive beyond EUR amount-threshold
