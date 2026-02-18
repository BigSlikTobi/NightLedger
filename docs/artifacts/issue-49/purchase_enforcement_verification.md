# Issue #49 Purchase Enforcement Verification Artifact

Date: 2026-02-18

## Scenario

Deterministic proof of purchase enforcement path:
`block -> approve -> execute`

## Captured terminal output

```text
STEP 1 PASS: authorize_action returned requires_approval for 500 EUR
STEP 2 PASS: purchase executor blocked without token
STEP 3 PASS: execution token mint blocked before approval
STEP 4 PASS: decision approved by human reviewer
STEP 5 PASS: execution token minted after approval
STEP 6 PASS: purchase executor succeeded with valid token
purchase-enforcement demo: PASS (decision_id=dec_29914cc1757f)
```

## Proof points

- `decision_id`: `dec_29914cc1757f`
- Step 1 response proves policy gate:
  - `state: requires_approval`
  - `reason_code: AMOUNT_ABOVE_THRESHOLD`
- Step 2 response proves fail-closed executor boundary:
  - `403 EXECUTION_TOKEN_MISSING`
- Step 3 response proves pre-approval mint is blocked:
  - `409 EXECUTION_DECISION_NOT_APPROVED`
- Step 5 response proves approval unlocks execution:
  - `execution_token` present
  - `action: purchase.create`
- Step 6 response proves authorized execution:
  - `status: executed`
  - `decision_id` echoed in execution receipt

## Regenerate

```bash
PYTHONPATH=src ./.venv/bin/python -m uvicorn nightledger_api.main:app --reload --port 8001
AUTO_START=0 bash tasks/smoke_purchase_enforcement_demo.sh
```
