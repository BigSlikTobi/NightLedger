# Event Schema v0

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

## Notes
- `title` + `details` are required for readable timeline output.
- `confidence` is optional but recommended.
- `timestamp` must include timezone information and is normalized to UTC.
- `approval.status` must transition through a valid state machine.
