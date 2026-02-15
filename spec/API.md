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

## GET /v1/runs/:runId/journal

Return rendered journal entries.

## POST /v1/approvals/:eventId

Resolve pending approval.

Request:

```json
{ "decision": "approved|rejected", "reason": "optional" }
```

## GET /v1/approvals/pending

List all pending approvals.
