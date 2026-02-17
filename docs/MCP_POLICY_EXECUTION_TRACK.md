# MCP + Policy Execution Track (Issue #67)

Parent cleanup umbrella: #62.

## Dependency-Ordered Phases

- Phase 1: MCP transport contract (#44)
- Phase 2: policy evaluation rule (#45)
- Phase 3: human approval flow (#46)
- Phase 4: runtime enforcement boundary (#47)
- Phase 5: append-only audit receipts (#48)
- Phase 6: deterministic demo proof path (#49)

Historical dependency anchor: #12
Historical dependency anchor: #13

## Retained Issue Boundaries

| Issue | Primary scope | Not in scope |
| --- | --- | --- |
| #44 | Transport contract only | policy thresholds, approval transitions, executor enforcement |
| #45 | Policy evaluation only | transport protocol shape, approval API, executor token verification |
| #46 | Approval state transition only | policy predicates, executor runtime guards, journal integrity hashing |
| #47 | Enforcement token verification only | policy authoring, approval-state mutation internals |
| #48 | Audit receipt integrity only | transport protocol evolution, approval UX flow logic |
| #49 | Demo orchestration only | new policy primitives or contract redesign |

Done criteria:

- Each retained issue ships only its primary scope in this table.
- No retained issue owns another issue's primary deliverable.

## User-Defined Rule Acceptance Criteria

- Policy input contract includes action type, currency, and numeric amount.
- Threshold example (v1): purchase.amount > 100 EUR -> requires_approval
- Boundary expectations: 100 EUR => allow, 101 EUR => requires_approval.
- Decision includes reason code: AMOUNT_ABOVE_THRESHOLD.

## MCP Integration Boundaries

| NightLedger ownership | External ownership |
| --- | --- |
| authorize_action contract validation and decision_id issuance | agent tool invocation wiring and retries |
| policy evaluation and approval state machine | business-side action execution (purchase processor) |
| append-only receipts and decision lookup APIs | fail-closed executor behavior when token is missing/invalid |

Governance enforcement stays in backend services, never in UI representation code.

## Superseded or Consolidated Issue Markers

| Issue | Marker | Canonical successor |
| --- | --- | --- |
| #12 | closed predecessor | superseded by #45 and #46 policy/approval split |
| #13 | closed predecessor | superseded by #48 for receipt integrity and ordering guardrails |

Canonical successor track owner: #67.
Parent link update required in #62.
