# API Draft v0

This is the canonical HTTP contract source for NightLedger runtime endpoints,
response envelopes, and endpoint-level behavior.

## POST /v1/mcp/authorize_action

Authorize an agent intent before an external side effect is executed.

Behavior (issue #45 policy threshold v1):

- Valid payload: `200 OK`
- Invalid payload: `422 Unprocessable Entity`
- Supported action in v1 policy path: `purchase.create`
- Policy inputs are required:
  - `context.amount` (numeric)
  - `context.currency` (`EUR`)
- Configurable threshold (default): `100` EUR
  - Environment override:
    `NIGHTLEDGER_PURCHASE_APPROVAL_THRESHOLD_EUR`
- Decision rule:
  - `amount <= threshold` => `state=allow`
  - `amount > threshold` => `state=requires_approval`
- `context.transport_decision_hint` remains accepted for request-shape
  compatibility, but policy evaluation is authoritative for final decision
- Every successful decision includes deterministic `decision_id`.

Request payload:

```json
{
  "intent": {
    "action": "purchase.create"
  },
  "context": {
    "request_id": "req_123",
    "amount": 101,
    "currency": "EUR",
    "transport_decision_hint": "requires_approval"
  }
}
```

## MCP stdio server: `authorize_action` tool

NightLedger also exposes the same transport contract through a local MCP stdio
server wrapper.

Supported MCP methods:

- `initialize`
- `notifications/initialized`
- `tools/list`
- `tools/call`

Tool name:

- `authorize_action`

Tool arguments:

```json
{
  "intent": {
    "action": "purchase.create"
  },
  "context": {
    "request_id": "req_123",
    "amount": 100,
    "currency": "EUR",
    "transport_decision_hint": "allow"
  }
}
```

Tool result (`tools/call`):

- `structuredContent` carries the decision object with:
  - `decision_id`
  - `state`
  - `reason_code`
- `isError=true` for invalid arguments, with a structured NightLedger error
  envelope in the response content and `structuredContent`.

Success responses:

`allow` (policy decision when amount is within threshold):

```json
{
  "decision_id": "dec_1d51e326dbd1e7f0",
  "state": "allow",
  "reason_code": "POLICY_ALLOW_WITHIN_THRESHOLD"
}
```

`requires_approval`:

```json
{
  "decision_id": "dec_8b43f6748da8bb2d",
  "state": "requires_approval",
  "reason_code": "AMOUNT_ABOVE_THRESHOLD"
}
```

Request validation error response:

```json
{
  "error": {
    "code": "REQUEST_VALIDATION_ERROR",
    "message": "authorize_action payload failed validation",
    "details": [
      {
        "path": "intent.action",
        "message": "Input should be 'purchase.create'",
        "type": "literal_error",
        "code": "UNSUPPORTED_ACTION"
      }
    ]
  }
}
```

Invalid decision hint example:

```json
{
  "error": {
    "code": "REQUEST_VALIDATION_ERROR",
    "message": "authorize_action payload failed validation",
    "details": [
      {
        "path": "context.transport_decision_hint",
        "message": "Input should be 'allow', 'requires_approval' or 'deny'",
        "type": "literal_error",
        "code": "INVALID_TRANSPORT_DECISION_HINT"
      }
    ]
  }
}
```

Missing amount example:

```json
{
  "error": {
    "code": "REQUEST_VALIDATION_ERROR",
    "message": "authorize_action payload failed validation",
    "details": [
      {
        "path": "context.amount",
        "message": "Field required",
        "type": "missing",
        "code": "MISSING_AMOUNT"
      }
    ]
  }
}
```

Unsupported currency example:

```json
{
  "error": {
    "code": "REQUEST_VALIDATION_ERROR",
    "message": "authorize_action payload failed validation",
    "details": [
      {
        "path": "context.currency",
        "message": "Input should be 'EUR'",
        "type": "literal_error",
        "code": "UNSUPPORTED_CURRENCY"
      }
    ]
  }
}
```

## POST /v1/events

Ingest one event.

Behavior:

- Valid payload: `201 Created` with
  `{"status": "accepted", "event_id": "...", "integrity_warning": false}`
- Invalid payload: `422 Unprocessable Entity`
- Governance/business-rule violation: `409 Conflict`
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

Governance constraints (runtime/business-rule boundary):

- `RULE-GATE-001`: `approval_requested` events must represent a pending gate
  state (`requires_approval=true` and `approval.status=pending`).
- `RULE-GATE-002`: `approval_resolved` events must be legal transitions from an
  existing pending gate.
- `RULE-GATE-011`: when an active pending approval includes
  `approval.decision_id`, the corresponding `approval_resolved` event must carry
  the same decision identifier.
- `RULE-RISK-005`: risky `action` events (`risk_level=high` or
  `requires_approval=true`) must include at least one evidence item.
- `RULE-GATE-010`: `summary` events are only legal for completion when no
  pending approval exists and summary approval fields indicate closed
  non-gated state.
- `RULE-GATE-007` and `RULE-GATE-008`: any `approved|rejected` approval status
  requires resolver metadata (`approval.resolved_by` and
  `approval.resolved_at`).
- `RULE-GATE-005`: terminal runs reject additional mutating event writes.

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

Governance violation response (v0 draft):

```json
{
  "error": {
    "code": "BUSINESS_RULE_VIOLATION",
    "message": "Event payload violates workflow governance rules",
    "details": [
      {
        "path": "approval.status",
        "message": "approval_requested must use approval.status='pending'",
        "type": "state_conflict",
        "code": "INVALID_APPROVAL_TRANSITION",
        "rule_id": "RULE-GATE-001"
      }
    ]
  }
}
```

Common approval-gate violation detail codes:

- `RULE-GATE-001`: `INVALID_APPROVAL_TRANSITION`
- `RULE-GATE-002`: `NO_PENDING_APPROVAL`
- `RULE-GATE-007`: `MISSING_APPROVER_ID`
- `RULE-GATE-008`: `MISSING_APPROVAL_TIMESTAMP`
- `RULE-GATE-005`: `TERMINAL_STATE_CONFLICT`
- `RULE-GATE-010`: `PENDING_APPROVAL_EXISTS`, `INVALID_SUMMARY_COMPLETION`

Common risk-governance violation detail codes:

- `RULE-RISK-005`: `MISSING_RISK_EVIDENCE`

Storage append error response (v0 draft):

## POST /v1/approvals/decisions/{decision_id}/execution-token

Mint an execution token for a previously approved `purchase.create` decision.

Behavior:

- `200 OK` when approval state is `approved` for `decision_id`.
- `409 Conflict` when approval is `pending` or `rejected`
  (`EXECUTION_DECISION_NOT_APPROVED`).
- Response includes:
  - `decision_id`
  - `action` (`purchase.create`)
  - `execution_token`
  - `expires_at`

## POST /v1/executors/purchase.create

Protected runtime executor for `purchase.create`.

Authorization:

- Requires `Authorization: Bearer <execution_token>`.

Verification rules:

- Token must be cryptographically valid.
- Token must be unexpired.
- Token action binding must match `purchase.create`.
- Token must be single-use; replay attempts fail.

Error detail codes:

- `EXECUTION_TOKEN_MISSING`
- `EXECUTION_TOKEN_INVALID`
- `EXECUTION_TOKEN_EXPIRED`
- `EXECUTION_TOKEN_REPLAYED`
- `EXECUTION_ACTION_MISMATCH`
- `EXECUTION_DECISION_NOT_APPROVED`

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

## GET /v1/runs/{run_id}/events

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

## GET /v1/runs/{run_id}/status

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
- journal projection entries missing readable `type`, `title`, or `details`
  return `INCONSISTENT_RUN_STATE` with detail code `MISSING_TIMELINE_FIELDS`.
- journal projection events whose `payload.id`/`payload.run_id` do not match the
  stored event identity return `INCONSISTENT_RUN_STATE` with detail code
  `TRACEABILITY_LINK_BROKEN`.
- journal projection risky `action` entries without evidence links return
  `INCONSISTENT_RUN_STATE` with detail code `MISSING_RISK_EVIDENCE`.
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

Return rendered journal entries.

Behavior:

- Existing run with consistent event stream: `200 OK`
- Unknown run: `404 Not Found` / `RUN_NOT_FOUND`
- Inconsistent state projection: `409 Conflict` / `INCONSISTENT_RUN_STATE`
- Storage read failure: `500 Internal Server Error` / `STORAGE_READ_ERROR`

Response shape (v0 draft):

```json
{
  "run_id": "run_123",
  "entry_count": 1,
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
- Approval context indicators: `approval_context.requires_approval`,
  `approval_context.status`, plus resolver fields when resolved

Deterministic projection semantics:

- Results are deterministic for the same append-only event stream.
- Entries are sorted by source event `timestamp` ascending.
- Timestamp ties are resolved by append sequence ascending.

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

- Parent: #5
- Related constraints: #13, #15

## POST /v1/approvals/requests

Register a pending approval request by `decision_id`.

Request:

```json
{
  "decision_id": "dec_8b43f6748da8bb2d",
  "run_id": "run_123",
  "requested_by": "agent",
  "title": "Approval required",
  "details": "Purchase amount exceeds threshold",
  "risk_level": "high",
  "reason": "Amount above configured EUR threshold"
}
```

Response (v0 draft):

```json
{
  "status": "registered",
  "decision_id": "dec_8b43f6748da8bb2d",
  "event_id": "evt_dec_approval_req_...",
  "run_id": "run_123",
  "approval_status": "pending"
}
```

Semantics:

- Appends an `approval_requested` receipt in append-only storage.
- Requires `approval.decision_id` link on the stored event payload.
- Fails with `DUPLICATE_APPROVAL` if the same `decision_id` already exists
  (pending or resolved lifecycle).

## POST /v1/approvals/decisions/{decision_id}

Resolve pending approval by `decision_id`.

Request:

```json
{
  "decision": "approved|rejected",
  "approver_id": "human_123",
  "reason": "optional"
}
```

Response shape matches legacy resolve contract with `decision_id` included.

## GET /v1/approvals/decisions/{decision_id}

Query approval lifecycle state for one `decision_id`.

Response (v0 draft):

```json
{
  "decision_id": "dec_8b43f6748da8bb2d",
  "run_id": "run_123",
  "status": "pending|approved|rejected",
  "requested_event_id": "evt_dec_approval_req_...",
  "resolved_event_id": "apr_evt_... or null",
  "requested_at": "2026-02-18T12:00:00Z",
  "resolved_at": "2026-02-18T12:01:00Z or null",
  "requested_by": "agent",
  "resolved_by": "human_123 or null",
  "reason": "optional"
}
```

## POST /v1/approvals/{event_id} (legacy compatibility)

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

Validation error response (v0 draft):

```json
{
  "error": {
    "code": "REQUEST_VALIDATION_ERROR",
    "message": "Approval request payload failed validation",
    "rule_ids": ["RULE-GATE-004", "RULE-GATE-007"],
    "details": [
      {
        "path": "decision",
        "message": "Input should be 'approved' or 'rejected'",
        "type": "literal_error",
        "code": "INVALID_APPROVAL_DECISION"
      },
      {
        "path": "approver_id",
        "message": "String should have at least 1 character",
        "type": "string_too_short",
        "code": "MISSING_APPROVER_ID"
      }
    ]
  }
}
```

Response (v0 draft):

```json
{
  "status": "resolved",
  "event_id": "apr_evt_123_approved_20260215T130100Z",
  "target_event_id": "evt_123",
  "run_id": "run_123",
  "decision": "approved",
  "resolved_at": "2026-02-15T13:01:00Z",
  "run_status": "approved|stopped|completed",
  "orchestration": {
    "applied": false,
    "event_ids": []
  },
  "timing": {
    "target_ms": 1000,
    "approval_to_state_update_ms": 42,
    "within_target": true,
    "orchestration_receipt_gap_ms": 2,
    "state_transition": "paused->completed"
  }
}
```

Error responses (v0 draft):

- Unknown target approval event: `404` / `APPROVAL_NOT_FOUND`
- Ambiguous target event ID across runs: `409` / `AMBIGUOUS_EVENT_ID`
- No currently pending approval for target: `409` / `NO_PENDING_APPROVAL`
- Duplicate approval conflict (already pending or already resolved):
  `409` / `DUPLICATE_APPROVAL`
- Storage append failure while writing approval resolution: `500` / `STORAGE_WRITE_ERROR`
- Stale resolution attempts for previously resolved targets return
  `DUPLICATE_APPROVAL` even if a different approval is currently pending.
- If post-approval orchestration appends fail after resolution write, return
  `500 STORAGE_WRITE_ERROR` and append a dedicated `error` receipt to the run
  journal (where storage permits) with terminal stop semantics.
  The storage detail message is
  `"triage_inbox orchestration append failed"`.

Resolution semantics:

- Approvals are modeled as append-only `approval_resolved` events.
- Legal transition is `pending -> approved|rejected`.
- `approver_id` and `resolved_at` must be present on resolved events.
- `decision="rejected"` writes terminal approval metadata for stop semantics.
- For the deterministic `triage_inbox` demo run (`run_triage_inbox_demo_1`),
  `decision="approved"` triggers orchestration resume events immediately after
  approval resolution only for the canonical seeded gate event
  (`target_event_id: "evt_triage_inbox_003"`):
  - a post-approval `action` event for resumed execution
  - a terminal `summary` event for completed workflow state
  This keeps the pause/resume transition explicit and auditable in append-only
  receipts.
- `run_status` reports the latest projected status after all resolution-side
  orchestration writes are complete.
- `orchestration.applied` and `orchestration.event_ids` expose whether
  additional continuation receipts were appended as part of this request.
- `timing.target_ms` is the MVP responsiveness contract for approval-to-state
  update at API boundary (`1000ms`).
- `timing.approval_to_state_update_ms` reports observed end-to-end processing
  time for resolution write + any continuation receipts + final run-state
  projection.
- `timing.approval_to_state_update_ms` is rounded up to the nearest integer
  millisecond (ceiling) to avoid under-reporting near threshold boundaries.
- `timing.within_target` confirms whether observed processing stayed within the
  MVP target and is equivalent to
  `approval_to_state_update_ms <= target_ms`.
- `timing.orchestration_receipt_gap_ms` reports deterministic logical timeline
  distance from `approval_resolved` to terminal orchestration receipt for the
  canonical `triage_inbox` completion flow (otherwise `null`).
- `timing.state_transition` reports approval-triggered state change observed by
  run status projection (for example `paused->completed`).
- Orchestration failures are fail-loud: they produce structured API errors and
  a journal-visible `error` event (`meta.step: "run_stopped"`) to prevent silent
  state mutation.
- This route remains supported for backward compatibility while decision-id
  callers migrate to `POST /v1/approvals/decisions/{decision_id}`.

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
    "message": "Approval already pending|Approval already resolved",
    "rule_ids": ["RULE-GATE-003"],
    "details": [
      {
        "path": "event_id|decision_id",
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
    "rule_ids": ["RULE-GATE-002"],
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
