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

## Deterministic triage_inbox setup

Reset and seed deterministic demo data:

```bash
bash tasks/reset_seed_triage_inbox_demo.sh
```

On setup failure, expect a structured error response and a structured log entry
containing `demo_seed_failed`.

Unexpected storage append failures surface as `STORAGE_WRITE_ERROR`.

## triage_inbox Orchestration Smoke Flow (Issue #51)

### 1) Seed deterministic paused demo run

```bash
curl -sS -X POST http://127.0.0.1:8001/v1/demo/triage_inbox/reset-seed
```

Expected:
- `200` with `run_id: "run_triage_inbox_demo_1"`
- `/v1/runs/run_triage_inbox_demo_1/status` reports `paused`

### 2) Approve the seeded risky step

```bash
curl -sS -X POST http://127.0.0.1:8001/v1/approvals/evt_triage_inbox_003 \
  -H "Content-Type: application/json" \
  -d '{
    "decision":"approved",
    "approver_id":"human_reviewer",
    "reason":"Approved for demo completion"
  }'
```

Expected:
- `200` with `status: "resolved"`
- backend appends explicit resume receipts for `triage_inbox`
- response includes `run_status: "completed"`
- response includes `orchestration.applied: true` with
  `event_ids: ["evt_triage_inbox_004", "evt_triage_inbox_005"]`
- orchestration applies only when resolving the canonical seeded demo target
  `evt_triage_inbox_003`; other approvals stay non-orchestrated
- if orchestration appends fail, expect `500 STORAGE_WRITE_ERROR` and a
  journal-visible `error` event that stops the run (`meta.step: run_stopped`)
- failure detail message should be:
  `triage_inbox orchestration append failed`

### 3) Verify terminal completion and receipts

```bash
curl -sS http://127.0.0.1:8001/v1/runs/run_triage_inbox_demo_1/status
curl -sS http://127.0.0.1:8001/v1/runs/run_triage_inbox_demo_1/journal
```

Expected:
- status endpoint reports `completed`
- journal includes `approval_resolved`, a resumed `action`, and terminal
  `summary` entries in deterministic order
- no silent state mutation: all lifecycle transitions are visible as events

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
- `run_status` reflects the latest projected status for that run
- `orchestration` indicates if additional continuation receipts were appended

### 4) Verify run status and pending list

```bash
curl -sS http://127.0.0.1:8001/v1/runs/run_approval_demo_1/status
curl -sS http://127.0.0.1:8001/v1/approvals/pending
```

Expected:
- run status: `approved`
- pending approvals no longer include the resolved target

## Journal Endpoint Smoke Flow (Issue #35)

The journal endpoint is the representation-layer projection for human-readable
timeline review while preserving references back to append-only source events.

### 1) Before approval resolution

Run this immediately after creating the pending approval event in step 1 above
(before resolving it):

```bash
curl -sS http://127.0.0.1:8001/v1/runs/run_approval_demo_1/journal
```

Expected:
- `200 OK`
- `entry_count >= 1`
- latest entry includes `approval_context.status: "pending"`
- latest entry includes `approval_indicator.is_approval_required: true`
- latest entry includes `approval_indicator.is_approval_resolved: false`

### 2) After approval resolution

Run this after resolving the approval in step 3 above:

```bash
curl -sS http://127.0.0.1:8001/v1/runs/run_approval_demo_1/journal
```

Expected:
- `200 OK`
- includes the original `approval_requested` entry and a later
  `approval_resolved` entry
- resolved entry includes `approval_context.status: "approved"`
- resolved entry includes non-null `approval_context.resolved_by` and
  `approval_context.resolved_at`
- resolved entry includes
  `approval_indicator: {"is_approval_required": true, "is_approval_resolved": true, "decision": "approved"}`

### 3) Journal response shape quick-check

Validate these core fields on each entry:

- identity and ordering: `entry_id`, `event_id`, `timestamp`
- readability: `event_type`, `title`, `details`
- evidence traceability to raw payload: `payload_ref.run_id`,
  `payload_ref.event_id`, `payload_ref.path`
- approval state projection: `approval_context`
- machine context: `metadata.actor`, `metadata.confidence`,
  `metadata.risk_level`, `metadata.integrity_warning`
- evidence list when present: `evidence_refs`
- approval transition marker when approval is relevant: `approval_indicator`

### 4) Journal error behavior quick-check

Unknown run:

```bash
curl -sS http://127.0.0.1:8001/v1/runs/run_journal_unknown/journal
```

Expected:
- `404 RUN_NOT_FOUND`
- error envelope has `error.code`, `error.message`, and `error.details[]`

Other documented failure classes:
- `409 INCONSISTENT_RUN_STATE` when stored run events are inconsistent or malformed.
- `500 STORAGE_READ_ERROR` when the backing store fails on read.

## Full Regression Suite

```bash
./.venv/bin/pytest -q
```
