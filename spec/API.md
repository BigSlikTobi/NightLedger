# API Draft v0

## POST /v1/events
Ingest one event.

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
