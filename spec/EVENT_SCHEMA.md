# Event Schema v0

This is the canonical payload schema for `POST /v1/events`.

## Canonical Field Names

All runtime/spec/rules docs use these names:

- `id`
- `run_id`
- `timestamp`
- `type`
- `actor`
- `title`
- `details`
- `confidence`
- `risk_level`
- `requires_approval`
- `approval`
- `evidence`
- `meta.workflow`
- `meta.step`

## Required vs Optional

Required fields for ingestion:

- `id`, `run_id`, `timestamp`, `type`, `actor`, `title`, `details`, `approval`

Optional fields:

- `confidence` (`0.0..1.0` when present)
- `risk_level` (`low|medium|high` when present)
- `requires_approval` (defaults to `false`)
- `evidence` (defaults to `[]`)
- `meta` (`workflow` + `step` required only when `meta` is provided)

## Validation Semantics

- Unknown fields are rejected.
- `timestamp` must include timezone information and is normalized to UTC.
- `title` and `details` must be non-empty strings.
- `approval.status` must be one of
  `not_required|pending|approved|rejected`.
- `approval.decision_id` is optional and may be used to link
  `authorize_action` decisions to approval lifecycle receipts.
- `evidence[*].kind` must be one of `log|url|artifact|diff`.

## JSON Shape

```json
{
  "id": "evt_...",
  "run_id": "run_...",
  "timestamp": "2026-02-14T13:00:00Z",
  "type": "intent|action|observation|decision|approval_requested|approval_resolved|error|summary",
  "actor": "agent|system|human",
  "title": "Short readable label",
  "details": "Human-readable explanation",
  "confidence": 0.0,
  "risk_level": "low|medium|high",
  "requires_approval": false,
  "approval": {
    "status": "not_required|pending|approved|rejected",
    "decision_id": "dec_...",
    "requested_by": "agent",
    "resolved_by": "human_id",
    "resolved_at": null,
    "reason": null
  },
  "evidence": [
    {
      "kind": "log|url|artifact|diff",
      "label": "Execution log",
      "ref": "..."
    }
  ],
  "meta": {
    "workflow": "triage_inbox",
    "step": "classify_priority"
  }
}
```
