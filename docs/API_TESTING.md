# API Testing Guide (Local)

This guide provides the fastest way to verify NightLedger API behavior on a
local machine.

## Prerequisites

- Run from repo root: `/Users/tobiaslatta/Projects/github/bigsliktobi/NightLedger`
- Python virtual environment exists at `.venv`
- API dependencies are installed in that venv

```bash
./.venv/bin/python -m pip install fastapi uvicorn pydantic pytest
```

## Start API

```bash
PYTHONPATH=src ./.venv/bin/python -m uvicorn nightledger_api.main:app --reload --port 8001
```

If you want to verify `uvicorn` is installed in the same interpreter used by
scripts:

```bash
./.venv/bin/python -c "import uvicorn; print(uvicorn.__version__)"
```

## Run Existing Status Smoke Script

```bash
bash tasks/smoke_status_curl.sh
```

Or against an already running API:

```bash
AUTO_START=0 BASE_URL=http://127.0.0.1:8001 bash tasks/smoke_status_curl.sh
```

## Approval Endpoint Smoke Flow (Issue #4)

### 1) Create a pending approval event

```bash
curl -sS -X POST http://127.0.0.1:8001/v1/events \
  -H "Content-Type: application/json" \
  -d '{
    "id":"evt_approval_demo_1",
    "run_id":"run_approval_demo_1",
    "timestamp":"2026-02-16T10:00:00Z",
    "type":"approval_requested",
    "actor":"agent",
    "title":"Approval required",
    "details":"Transfer exceeds threshold",
    "confidence":0.8,
    "risk_level":"high",
    "requires_approval":true,
    "approval":{
      "status":"pending",
      "requested_by":"agent",
      "resolved_by":null,
      "resolved_at":null,
      "reason":"Transfer exceeds threshold"
    },
    "evidence":[{"kind":"log","label":"Execution log","ref":"log://approval-demo"}]
  }'
```

Expected: `201` with `{"status":"accepted", ...}`

### 2) List pending approvals

```bash
curl -sS http://127.0.0.1:8001/v1/approvals/pending
```

Expected: `pending_count >= 1` and an entry for `evt_approval_demo_1`.

### 3) Resolve approval

```bash
curl -sS -X POST http://127.0.0.1:8001/v1/approvals/evt_approval_demo_1 \
  -H "Content-Type: application/json" \
  -d '{
    "decision":"approved",
    "approver_id":"human_reviewer",
    "reason":"Looks safe"
  }'
```

Expected: `200` with:
- `status: "resolved"`
- `target_event_id: "evt_approval_demo_1"`
- `decision: "approved"`

### 4) Verify run status and pending list

```bash
curl -sS http://127.0.0.1:8001/v1/runs/run_approval_demo_1/status
curl -sS http://127.0.0.1:8001/v1/approvals/pending
```

Expected:
- run status: `approved`
- pending approvals no longer include the resolved target

## Full Regression Suite

```bash
./.venv/bin/pytest -q
```

