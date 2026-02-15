# Demo Script

## Goal

Demonstrate that NightLedger provides autonomy with receipts:
- operators can read the projected journal quickly
- every projected entry can be traced to append-only evidence
- risky actions pause until human approval is explicitly recorded

## Setup

1. Start API:

```bash
PYTHONPATH=src ./.venv/bin/python -m uvicorn nightledger_api.main:app --reload --port 8001
```

2. Open web app and select a run ID for demo narration.

## Live Flow

### 1) Ingest an approval-required event

Use the same event from `docs/API_TESTING.md` with:
- `event_id: evt_approval_demo_1`
- `run_id: run_approval_demo_1`
- `type: approval_requested`
- `approval.status: pending`

### 2) Journal readability demo

Call the projection endpoint:

```bash
curl -sS http://127.0.0.1:8001/v1/runs/run_approval_demo_1/journal
```

Narration points:
- the entry is readable at a glance (`title`, `details`, `event_type`)
- approval pause is visible in `approval_context.status: pending`
- `approval_indicator` flags this as approval-required

### 3) Evidence traceability demo

From the same journal response, show:
- `payload_ref.path` points to `/v1/runs/run_approval_demo_1/events#evt_approval_demo_1`
- `evidence_refs` contains raw evidence pointers (for example `log://...`)
- this proves the projection is a view, not a mutable source of truth

### 4) Before approval resolution

Call `GET /v1/runs/{run_id}/journal` and pause on the pending entry:
- confirm unresolved state in `approval_context.resolved_by: null`
- confirm unresolved state in `approval_context.resolved_at: null`
- confirm `approval_indicator.is_approval_resolved: false`

### 5) Resolve approval

Approve the pending request (CLI or UI):

```bash
curl -sS -X POST http://127.0.0.1:8001/v1/approvals/evt_approval_demo_1 \
  -H "Content-Type: application/json" \
  -d '{"decision":"approved","approver_id":"human_reviewer","reason":"Looks safe"}'
```

### 6) After approval resolution

Call `GET /v1/runs/{run_id}/journal` again and highlight:
- a new `approval_resolved` entry is appended
- `approval_context.status` is now `approved`
- `approval_context.resolved_by` and `approval_context.resolved_at` are set
- `approval_indicator` now shows resolved decision context

### 7) Close with run status

```bash
curl -sS http://127.0.0.1:8001/v1/runs/run_approval_demo_1/status
```

Final point:
- journal readability and evidence traceability remain intact across the pause
  and resolution transition.
