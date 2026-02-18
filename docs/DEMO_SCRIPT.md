# Demo Script

## Goal

Demonstrate the canonical `triage_inbox` vertical slice:
- risky step pauses in an auditable way
- human approval resumes to terminal completion
- every transition is explainable through receipts

## Reproducible Command Path (Issue #54)

### 0) Start API in a persistent terminal session

```bash
PYTHONPATH=src ./.venv/bin/python -m uvicorn nightledger_api.main:app --reload --port 8001
```

Keep this process running while you execute the remaining steps in a second
terminal.

### 1) Reset and seed deterministic demo state

```bash
AUTO_START=0 bash tasks/reset_seed_triage_inbox_demo.sh
```

Expected output:
- `status: "seeded"`
- `run_id: "run_triage_inbox_demo_1"`
- `event_count: 3`
- `seeded_event_ids` includes:
  `evt_triage_inbox_001`, `evt_triage_inbox_002`, `evt_triage_inbox_003`

### 2) Verify run is paused before approval

```bash
curl -sS http://127.0.0.1:8001/v1/runs/run_triage_inbox_demo_1/status
```

Expected output:
- `status: "paused"`
- `pending_approval.event_id: "evt_triage_inbox_003"`

### Journal readability demo

Call the journal endpoint:

```bash
curl -sS http://127.0.0.1:8001/v1/runs/run_triage_inbox_demo_1/journal
```

Narration points:
- readable lifecycle context (`event_type`, `title`, `details`)
- explicit pending state in `approval_context.status: "pending"`
- approval transition marker via `approval_indicator`

### Evidence traceability demo

From the same journal response:
- verify `payload_ref.path` points back to `/v1/runs/run_triage_inbox_demo_1/events#...`
- verify `evidence_refs` preserve raw source links
- confirm projection remains representation-only (no core log mutation)

### Before approval resolution

On `GET /v1/runs/{run_id}/journal`:
- `approval_context.resolved_by: null`
- `approval_context.resolved_at: null`
- `approval_indicator.is_approval_resolved: false`

### 3) Resolve canonical approval gate

```bash
curl -sS -X POST http://127.0.0.1:8001/v1/approvals/evt_triage_inbox_003 \
  -H "Content-Type: application/json" \
  -d '{"decision":"approved","approver_id":"human_reviewer","reason":"Approved for demo completion"}'
```

Expected output:
- `status: "resolved"`
- `run_status: "completed"`
- `orchestration.applied: true`
- `orchestration.event_ids: ["evt_triage_inbox_004","evt_triage_inbox_005"]`
- `timing.target_ms: 1000`
- `timing.state_transition: "paused->completed"`

### After approval resolution

Re-check `GET /v1/runs/{run_id}/journal`:
- includes appended `approval_resolved` entry
- `approval_context.status: "approved"`
- non-null `approval_context.resolved_by` and `approval_context.resolved_at`
- `approval_indicator` reflects resolved decision

### 4) Verify terminal run status

```bash
curl -sS http://127.0.0.1:8001/v1/runs/run_triage_inbox_demo_1/status
```

Expected output:
- `status: "completed"`
- `pending_approval: null`

## Purchase Enforcement Command Path (Issue #49)

This additive path proves the purchase flow
`block -> approve -> execute` with deterministic operator output.

### 0) Start API in a persistent terminal session

```bash
PYTHONPATH=src ./.venv/bin/python -m uvicorn nightledger_api.main:app --reload --port 8001
```

### 1) Run one-command purchase enforcement proof

```bash
AUTO_START=0 bash tasks/smoke_purchase_enforcement_demo.sh
```

Expected output includes these deterministic proof lines:
- `STEP 1 PASS: authorize_action returned requires_approval for 500 EUR`
- `STEP 2 PASS: purchase executor blocked without token`
- `STEP 3 PASS: execution token mint blocked before approval`
- `STEP 4 PASS: decision approved by human reviewer`
- `STEP 5 PASS: execution token minted after approval`
- `STEP 6 PASS: purchase executor succeeded with valid token`
- `purchase-enforcement demo: PASS`

## Purchase Enforcement Evidence Checklist (Issue #49)

| Step | Endpoint/Action | Receipt evidence to show |
| --- | --- | --- |
| 1 | `POST /v1/mcp/authorize_action` | response has `state: requires_approval`, `reason_code: AMOUNT_ABOVE_THRESHOLD`, deterministic `decision_id` |
| 2 | `POST /v1/executors/purchase.create` (no token) | blocked with `403 EXECUTION_TOKEN_MISSING` |
| 3 | `POST /v1/approvals/requests` then `POST /v1/approvals/decisions/{decision_id}/execution-token` | pending decision token mint blocked with `409 EXECUTION_DECISION_NOT_APPROVED` |
| 4 | `POST /v1/approvals/decisions/{decision_id}` | approval resolution returns `status: resolved`, `decision: approved` |
| 5 | `POST /v1/approvals/decisions/{decision_id}/execution-token` | token minted after approval (`execution_token` present) |
| 6 | `POST /v1/executors/purchase.create` (valid token) | executor succeeded with valid token and returns `status: executed` |

## Real Bot Workflow (Issue #49 v1)

This section is for a real bot integration (no simulation):

1. Bot calls MCP `authorize_action`.
2. If `allow`, bot proceeds.
3. If `requires_approval`, bot pauses.
4. Bot posts `POST /v1/approvals/requests`.
5. User approves/rejects in UI.
6. Bot polls `GET /v1/approvals/decisions/{decision_id}`.
7. Bot resumes only after approved state, then mints token and executes.

UI step:

- user approves/rejects in UI at:
  `http://localhost:3000/view/?mode=live&runId=<run_id>&apiBase=http://127.0.0.1:8001`

Bot polling step:

- bot polls GET /v1/approvals/decisions/{decision_id}

## Troubleshooting

What to check when demo flow fails:

- Symptom: `API did not become ready at http://127.0.0.1:8001`
  What to check:
  - run `curl -sS http://127.0.0.1:8001/openapi.json`
  - verify `.venv` exists and `uvicorn` is installed
  - retry `bash tasks/reset_seed_triage_inbox_demo.sh`

- Symptom: approval request returns `NO_PENDING_APPROVAL`
  What to check:
  - re-run seed script and confirm paused state first
  - ensure target event is exactly `evt_triage_inbox_003`
  - confirm `GET /v1/runs/run_triage_inbox_demo_1/status` shows `paused`

- Symptom: status/journal call returns `RUN_NOT_FOUND`
  What to check:
  - run seed step again and confirm `run_id: "run_triage_inbox_demo_1"`
  - verify there was no API restart between seed and query

## Evidence Checklist

| Step | Endpoint/Action | Receipt evidence to show |
| --- | --- | --- |
| 1 | `POST /v1/demo/triage_inbox/reset-seed` (`reset-seed`) | seeded IDs include `evt_triage_inbox_001..003` |
| 2 | `GET /v1/runs/run_triage_inbox_demo_1/status` | paused gate with pending approval on `evt_triage_inbox_003` (`approval_requested`) |
| 2b | `GET /v1/runs/run_triage_inbox_demo_1/journal` | pending marker via `approval_context.status: pending` and `approval_indicator` |
| 3 | `POST /v1/approvals/evt_triage_inbox_003` | resolved receipt includes `approval_resolved`, timing block, and orchestration IDs |
| 3b | orchestration receipts | explicit continuation entries `evt_triage_inbox_004` and `evt_triage_inbox_005` |
| 4 | `GET /v1/runs/run_triage_inbox_demo_1/status` | terminal `completed` state with `pending_approval: null` |

## Operator Handoff

### Teammate execution checklist

- run the command path in order without editing payloads
- capture outputs for seed, paused status, approval response, and completed status
- verify receipt IDs and timing fields are present in approval response

### Go/No-Go

- `GO` when all are true:
  - `run_status: "completed"`
  - `orchestration.applied: true`
  - `timing.within_target: true`
  - journal and status outputs match the evidence checklist above
- `NO-GO` if any check fails; include the failing response body in handoff notes
