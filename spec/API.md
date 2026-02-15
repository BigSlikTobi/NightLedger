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
