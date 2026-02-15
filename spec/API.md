# API Draft v0

## POST /v1/events

Ingest one event.

Behavior:

- Valid payload: `201 Created` with
  `{"status": "accepted", "event_id": "...", "integrity_warning": false}`
- Invalid payload: `422 Unprocessable Entity`
- Duplicate event ID within run: `409 Conflict`
- Storage append failure: `500 Internal Server Error`

Required payload fields (schema v0 boundary):

- `id`, `run_id`, `timestamp`, `type`, `actor`, `title`, `details`, `approval`

Field constraints:

- `id` and `run_id` must be non-empty strings.
- `title` and `details` must be non-empty strings.
- `confidence` (if provided) must be between `0.0` and `1.0` (inclusive).
- `timestamp` must include timezone and is normalized to UTC (`Z`) internally.
- Unknown fields are rejected.

Validation error response (v0 draft):

```json
{
  "error": {
    "code": "SCHEMA_VALIDATION_ERROR",
    "message": "Event payload failed schema validation",
    "details": [
      {
        "path": "type",
        "message": "Field required",
        "type": "missing",
        "code": "MISSING_EVENT_TYPE"
      }
    ]
  }
}
```

Storage append error response (v0 draft):

```json
{
  "error": {
    "code": "STORAGE_WRITE_ERROR",
    "message": "Failed to persist event",
    "details": [
      {
        "path": "storage",
        "message": "storage backend append failed",
        "type": "storage_failure",
        "code": "STORAGE_APPEND_FAILED"
      }
    ]
  }
}
```

Duplicate event error response (v0 draft):

```json
{
  "error": {
    "code": "DUPLICATE_EVENT_ID",
    "message": "Event ID already exists for this run",
    "details": [
      {
        "path": "event_id",
        "message": "Event ID 'evt_123' already exists for run 'run_123'",
        "type": "duplicate_event",
        "code": "DUPLICATE_EVENT_ID"
      }
    ]
  }
}
```

## GET /v1/runs/:runId/events

List events for a run (deterministic ascending by time).

Response (v0 draft):

```json
{
  "run_id": "run_123",
  "event_count": 1,
  "events": [
    {
      "id": "evt_123",
      "timestamp": "2026-02-14T13:00:00Z",
      "run_id": "run_123",
      "payload": {
        "...": "validated event payload"
      },
      "integrity_warning": false
    }
  ]
}
```

## GET /v1/runs/:runId/status

Project current workflow status from immutable run events.

Behavior:

- Existing run with consistent event stream: `200 OK`
- Unknown run: `404 Not Found`
- Inconsistent state projection: `409 Conflict`
- Storage read failure: `500 Internal Server Error`

Response (v0 draft):

```json
{
  "run_id": "run_123",
  "status": "paused",
  "pending_approval": {
    "event_id": "evt_approval_1",
    "requested_by": "agent",
    "requested_at": "2026-02-14T13:00:00Z",
    "reason": "Transfer exceeds policy threshold"
  }
}
```

Status values:

- `running`
- `paused`
- `approved`
- `rejected`
- `stopped`
- `expired`
- `completed`

Projection precedence (highest to lowest):

1. `expired`: latest terminal event indicates timeout/expiration.
2. `stopped`: latest terminal event indicates stop/rejection.
3. `completed`: latest terminal event indicates normal completion.
4. `rejected`: latest approval resolution is rejected.
5. `approved`: latest approval resolution is approved.
6. `paused`: latest unresolved approval is pending.
7. `running`: default for consistent non-terminal runs.

Pending approval context rules:

- `pending_approval` is required when `status` is `paused`.
- `pending_approval` must be `null` for all non-`paused` statuses.

Unknown run error response (v0 draft):

```json
{
  "error": {
    "code": "RUN_NOT_FOUND",
    "message": "Run not found",
    "details": [
      {
        "path": "run_id",
        "message": "No events found for run 'run_123'",
        "type": "not_found",
        "code": "RUN_NOT_FOUND"
      }
    ]
  }
}
```

Inconsistent state error response (v0 draft):

```json
{
  "error": {
    "code": "INCONSISTENT_RUN_STATE",
    "message": "Run events contain inconsistent approval state",
    "details": [
      {
        "path": "approval",
        "message": "approval_resolved encountered without pending approval",
        "type": "state_conflict",
        "code": "NO_PENDING_APPROVAL"
      }
    ]
  }
}
```

Additional inconsistent-state cases:

- `approval_resolved` event with `approval.status` not in `approved|rejected`
  returns `INCONSISTENT_RUN_STATE` with detail code `INVALID_APPROVAL_TRANSITION`.
- More than one pending approval without an intervening resolution returns
  `INCONSISTENT_RUN_STATE` with detail code `DUPLICATE_PENDING_APPROVAL`.
- `approval_resolved` event missing `approval.resolved_by` returns
  `INCONSISTENT_RUN_STATE` with detail code `MISSING_APPROVER_ID`.
- `approval_resolved` event missing `approval.resolved_at` returns
  `INCONSISTENT_RUN_STATE` with detail code `MISSING_APPROVAL_TIMESTAMP`.
- Any non-terminal event encountered after status `rejected` returns
  `INCONSISTENT_RUN_STATE` with detail code `REJECTED_STATE_CONFLICT`.
- Any non-terminal event encountered after a terminal status marker (`completed`,
  `stopped`, `expired`) returns `INCONSISTENT_RUN_STATE` with detail code
  `TERMINAL_STATE_CONFLICT`.

Storage read error response (v0 draft):

```json
{
  "error": {
    "code": "STORAGE_READ_ERROR",
    "message": "Failed to load events",
    "details": [
      {
        "path": "storage",
        "message": "storage backend read failed",
        "type": "storage_failure",
        "code": "STORAGE_READ_FAILED"
      }
    ]
  }
}
```

## GET /v1/runs/{run_id}/journal

Return rendered journal entries for one run.

Behavior:

- Existing run with consistent event stream: `200 OK`
- Unknown run: `404 Not Found` / `RUN_NOT_FOUND`
- Inconsistent state projection: `409 Conflict` / `INCONSISTENT_RUN_STATE`
- Storage read failure: `500 Internal Server Error` / `STORAGE_READ_ERROR`

Deterministic projection semantics:

- Results are deterministic for the same underlying append-only log.
- Entries are sorted by event `timestamp` ascending.
- Timestamp ties are resolved by append sequence ascending (first appended first).
- No UI-only mutations are applied in this endpoint; projection is read-only.

Response shape (v0 draft):

```json
{
  "run_id": "run_123",
  "entry_count": 2,
  "entries": [
    {
      "entry_id": "jrnl_run_123_0001",
      "event_id": "evt_approval_1",
      "timestamp": "2026-02-14T13:00:00Z",
      "event_type": "approval_requested",
      "title": "Approval required",
      "details": "Transfer exceeds policy threshold",
      "payload_ref": {
        "run_id": "run_123",
        "event_id": "evt_approval_1",
        "path": "/v1/runs/run_123/events#evt_approval_1"
      },
      "approval_context": {
        "requires_approval": true,
        "status": "pending",
        "requested_by": "agent",
        "resolved_by": null,
        "resolved_at": null,
        "reason": "Transfer exceeds policy threshold"
      }
    }
  ]
}
```

Minimum entry fields:

- Human-readable text: `title`, `details`
- Event traceability: `event_id`, `payload_ref`
- Approval indicators: `approval_context.requires_approval`,
  `approval_context.status`, plus resolver fields when resolved

Error envelope format:

- Matches existing API error envelope:
  `{"error":{"code":"...","message":"...","details":[...]}}`
- `404` uses `RUN_NOT_FOUND`
- `409` uses `INCONSISTENT_RUN_STATE`
- `500` uses `STORAGE_READ_ERROR`

Example — pending approval flow:

```json
{
  "run_id": "run_approval_pending",
  "entry_count": 2,
  "entries": [
    {
      "entry_id": "jrnl_run_approval_pending_0001",
      "event_id": "evt_init_1",
      "timestamp": "2026-02-15T09:00:00Z",
      "event_type": "action",
      "title": "Start transfer workflow",
      "details": "Agent prepared transfer request",
      "payload_ref": {
        "run_id": "run_approval_pending",
        "event_id": "evt_init_1",
        "path": "/v1/runs/run_approval_pending/events#evt_init_1"
      },
      "approval_context": {
        "requires_approval": false,
        "status": "not_required",
        "requested_by": null,
        "resolved_by": null,
        "resolved_at": null,
        "reason": null
      }
    },
    {
      "entry_id": "jrnl_run_approval_pending_0002",
      "event_id": "evt_approval_req_1",
      "timestamp": "2026-02-15T09:01:00Z",
      "event_type": "approval_requested",
      "title": "Approval required",
      "details": "Transfer exceeds policy threshold",
      "payload_ref": {
        "run_id": "run_approval_pending",
        "event_id": "evt_approval_req_1",
        "path": "/v1/runs/run_approval_pending/events#evt_approval_req_1"
      },
      "approval_context": {
        "requires_approval": true,
        "status": "pending",
        "requested_by": "agent",
        "resolved_by": null,
        "resolved_at": null,
        "reason": "Transfer exceeds policy threshold"
      }
    }
  ]
}
```

Example — post-resolution flow:

```json
{
  "run_id": "run_approval_resolved",
  "entry_count": 3,
  "entries": [
    {
      "entry_id": "jrnl_run_approval_resolved_0001",
      "event_id": "evt_init_1",
      "timestamp": "2026-02-15T10:00:00Z",
      "event_type": "action",
      "title": "Start transfer workflow",
      "details": "Agent prepared transfer request",
      "payload_ref": {
        "run_id": "run_approval_resolved",
        "event_id": "evt_init_1",
        "path": "/v1/runs/run_approval_resolved/events#evt_init_1"
      },
      "approval_context": {
        "requires_approval": false,
        "status": "not_required",
        "requested_by": null,
        "resolved_by": null,
        "resolved_at": null,
        "reason": null
      }
    },
    {
      "entry_id": "jrnl_run_approval_resolved_0002",
      "event_id": "evt_approval_req_1",
      "timestamp": "2026-02-15T10:01:00Z",
      "event_type": "approval_requested",
      "title": "Approval required",
      "details": "Transfer exceeds policy threshold",
      "payload_ref": {
        "run_id": "run_approval_resolved",
        "event_id": "evt_approval_req_1",
        "path": "/v1/runs/run_approval_resolved/events#evt_approval_req_1"
      },
      "approval_context": {
        "requires_approval": true,
        "status": "pending",
        "requested_by": "agent",
        "resolved_by": null,
        "resolved_at": null,
        "reason": "Transfer exceeds policy threshold"
      }
    },
    {
      "entry_id": "jrnl_run_approval_resolved_0003",
      "event_id": "evt_approval_res_1",
      "timestamp": "2026-02-15T10:02:00Z",
      "event_type": "approval_resolved",
      "title": "Approval decision recorded",
      "details": "Human reviewer approved transfer",
      "payload_ref": {
        "run_id": "run_approval_resolved",
        "event_id": "evt_approval_res_1",
        "path": "/v1/runs/run_approval_resolved/events#evt_approval_res_1"
      },
      "approval_context": {
        "requires_approval": true,
        "status": "approved",
        "requested_by": "agent",
        "resolved_by": "human_reviewer",
        "resolved_at": "2026-02-15T10:02:00Z",
        "reason": "Within policy after manual verification"
      }
    }
  ]
}
```

Issue links:

- Parent contract requirement: #5
- Related follow-up constraints: #13, #15

## POST /v1/approvals/:eventId

Resolve pending approval.

Request:

```json
{
  "decision": "approved|rejected",
  "approver_id": "human_123",
  "reason": "optional"
}
```

`approver_id` must be a non-empty, non-whitespace string.

Response (v0 draft):

```json
{
  "status": "resolved",
  "event_id": "apr_evt_123_approved_20260215T130100Z",
  "target_event_id": "evt_123",
  "run_id": "run_123",
  "decision": "approved",
  "resolved_at": "2026-02-15T13:01:00Z"
}
```

Error responses (v0 draft):

- Unknown target approval event: `404` / `APPROVAL_NOT_FOUND`
- Ambiguous target event ID across runs: `409` / `AMBIGUOUS_EVENT_ID`
- No currently pending approval for target: `409` / `NO_PENDING_APPROVAL`
- Target approval already resolved: `409` / `DUPLICATE_APPROVAL`
- Storage append failure while writing approval resolution: `500` / `STORAGE_WRITE_ERROR`
- Stale resolution attempts for previously resolved targets return
  `DUPLICATE_APPROVAL` even if a different approval is currently pending.

Resolution semantics:

- Approvals are modeled as append-only `approval_resolved` events.
- Legal transition is `pending -> approved|rejected`.
- `approver_id` and `resolved_at` must be present on resolved events.
- `decision="rejected"` writes terminal approval metadata for stop semantics.

Ambiguous event ID error response (v0 draft):

```json
{
  "error": {
    "code": "AMBIGUOUS_EVENT_ID",
    "message": "Event ID maps to multiple runs",
    "details": [
      {
        "path": "event_id",
        "message": "Event ID 'evt_123' exists in multiple runs",
        "type": "state_conflict",
        "code": "AMBIGUOUS_EVENT_ID"
      }
    ]
  }
}
```

Duplicate approval error response (v0 draft):

```json
{
  "error": {
    "code": "DUPLICATE_APPROVAL",
    "message": "Approval already resolved",
    "details": [
      {
        "path": "event_id",
        "message": "Approval for event 'evt_123' has already been resolved",
        "type": "state_conflict",
        "code": "DUPLICATE_APPROVAL"
      }
    ]
  }
}
```

No pending approval error response (v0 draft):

```json
{
  "error": {
    "code": "NO_PENDING_APPROVAL",
    "message": "No pending approval for target event",
    "details": [
      {
        "path": "event_id",
        "message": "Event 'evt_123' is not the currently pending approval",
        "type": "state_conflict",
        "code": "NO_PENDING_APPROVAL"
      }
    ]
  }
}
```

## GET /v1/approvals/pending

List all pending approvals.

Response (v0 draft):

```json
{
  "pending_count": 1,
  "approvals": [
    {
      "event_id": "evt_123",
      "run_id": "run_123",
      "requested_at": "2026-02-15T13:00:00Z",
      "requested_by": "agent",
      "title": "Approval required",
      "details": "Transfer exceeds threshold",
      "reason": "Transfer exceeds threshold",
      "risk_level": "high"
    }
  ]
}
```

Behavior:

- Returns unresolved pending approvals across all runs.
- Intended for polling/UI refresh; payload is stable and deterministic.
- If any run contains an inconsistent approval timeline, endpoint returns `409`
  / `INCONSISTENT_RUN_STATE` (fail-loud semantics).
