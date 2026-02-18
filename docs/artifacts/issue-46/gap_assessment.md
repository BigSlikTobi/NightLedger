# Issue #46 Post-Implementation Gap Assessment

Date: 2026-02-18

## 1) Did #46 close the decision_id approval lifecycle?

Mostly yes for v1 scope:

- Added pending registration by decision id:
  `POST /v1/approvals/requests`
- Added decision resolution by decision id:
  `POST /v1/approvals/decisions/{decision_id}`
- Added decision lookup:
  `GET /v1/approvals/decisions/{decision_id}`
- Added event-schema support for `approval.decision_id`.
- Added governance validation for decision-id mismatch on resolution
  (`APPROVAL_DECISION_ID_MISMATCH` / `RULE-GATE-011`).
- Preserved legacy compatibility route:
  `POST /v1/approvals/{event_id}`.

## 2) Remaining blockers for #47 (token-gated executor)

- No signed or verifiable execution token/receipt exists yet.
- No protected `purchase.create` executor boundary exists.
- No replay/tamper token checks are implemented.

## 3) Remaining blockers for #48 (tamper-evident integrity chain)

- Append-only behavior exists, but no hash-chain (`hash`/`prev_hash`) integrity
  proof is implemented.
- No export format proving tamper evidence for a full decision trace.

## 4) Remaining blockers for #49 (500 EUR block -> approve -> execute demo)

- Current deterministic demo is still `triage_inbox` oriented.
- No packaged purchase-specific script that demonstrates:
  - `authorize_action(500 EUR) -> requires_approval`
  - blocked executor without approval token
  - approved token path to successful execution
  - full receipt trail.

## 5) Contract drift risks

- Moderate risk remains if both approval paths evolve independently
  (`decision_id` and legacy `event_id` route).
- Risk is currently controlled by API tests and doc-lock tests, but eventual
  deprecation criteria for legacy route should be defined in #47 or a follow-up.

## 6) Label/status hygiene recommendations

- Re-evaluate `status:blocked` labels on `#46/#47/#48/#49` now that #46 runtime
  scope has shipped.
- Keep #62 cleanup parent updated with links to this implementation and remaining
  blockers.
- Add explicit cross-links from #47/#48/#49 back to this artifact for dependency
  context.
