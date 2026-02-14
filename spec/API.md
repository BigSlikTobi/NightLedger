# API Draft v0

## POST /v1/events
Ingest one event.

Behavior:
- Valid payload: `201 Created`
- Invalid payload: `422 Unprocessable Entity`

Required payload fields (schema v0 boundary):
- `id`, `run_id`, `timestamp`, `type`, `actor`, `title`, `details`, `approval`

Field constraints:
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

## GET /v1/runs/:runId/events
List events for a run (ascending by time).

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
