# NightLedger Business Rules

This document defines canonical governance and projection rules for runtime
behavior. This rule catalog uses the same field names as
`spec/EVENT_SCHEMA.md` and `spec/API.md`.

## Canonical Naming

| Contract field | Meaning |
| --- | --- |
| `id` | Event identifier, unique within a run |
| `run_id` | Run partition key |
| `type` | Event category |
| `actor` | Event producer role |
| `meta.workflow` | Workflow namespace label |
| `meta.step` | Lifecycle step label |

## Constants

| Constant | Value | Rationale |
| --- | --- | --- |
| `CONFIDENCE_THRESHOLD` | `0.4` | Advisory threshold for review intensity |
| `APPROVAL_TIMEOUT` | TBD | Expiration boundary for pending approvals |

## Core Integrity (Append-Only)

### RULE-CORE-001: Run ID Requirement

- Needs: `run_id`
- Rule:
  - IF `run_id` is missing or empty
  - THEN reject with `MISSING_RUN_ID`

### RULE-CORE-002: Event ID Requirement

- Needs: `id`
- Rule:
  - IF `id` is missing or empty
  - THEN reject with `MISSING_EVENT_ID`

### RULE-CORE-003: Duplicate Prevention

- Needs: `id`, `run_id`
- Rule:
  - IF `id` already exists within the same `run_id`
  - THEN reject with `DUPLICATE_EVENT_ID`

### RULE-CORE-004: Timestamp Requirement

- Needs: `timestamp`
- Rule:
  - IF `timestamp` is missing
  - THEN reject with `MISSING_TIMESTAMP`
  - IF `timestamp` is not timezone-aware
  - THEN reject with `INVALID_TIMESTAMP`

### RULE-CORE-005: Out-of-Order Receipt Handling

- Needs: current `timestamp`, prior `timestamp`
- Rule:
  - IF `timestamp` is older than the latest stored event in a run
  - THEN append event and set `integrity_warning=true`

### RULE-CORE-006: Type Requirement

- Needs: `type`
- Rule:
  - IF `type` is missing
  - THEN reject with `MISSING_EVENT_TYPE`

### RULE-CORE-007: Type Validation

- Needs: `type`
- Valid values:
  - `intent|action|observation|decision|approval_requested|approval_resolved|error|summary`
- Rule:
  - IF `type` is not in valid values
  - THEN reject with `INVALID_EVENT_TYPE`

### RULE-CORE-008: Actor Validation

- Needs: `actor`
- Valid values:
  - `agent|system|human`
- Rule:
  - IF `actor` is missing or invalid
  - THEN reject with `INVALID_ACTOR`

### RULE-CORE-009: Readability Requirement

- Needs: `title`, `details`
- Rule:
  - IF `title` or `details` is missing/empty
  - THEN reject with `MISSING_TIMELINE_FIELDS`

## Risk Labeling

### RULE-RISK-001: Workflow Metadata Shape

- Needs: `meta.workflow`, `meta.step`
- Rule:
  - IF `meta` is present, both `meta.workflow` and `meta.step` must be
    non-empty strings

### RULE-RISK-002: Risk Level Contract

- Needs: `risk_level`
- Rule:
  - `risk_level` may be omitted
  - IF present, it must be `low|medium|high`
  - otherwise reject with `INVALID_RISK_LEVEL`

### RULE-RISK-003: Approval Flag and Status Consistency

- Needs: `requires_approval`, `approval.status`
- Rule:
  - IF `requires_approval=true`, `approval.status` must be
    `pending|approved|rejected`
  - IF `requires_approval=false`, `approval.status` is typically
    `not_required`

### RULE-RISK-004: Unknown Field Rejection

- Needs: payload shape
- Rule:
  - IF unknown fields are present at any schema level
  - THEN reject with `UNKNOWN_FIELD`

### RULE-RISK-005: Risky Action Evidence Requirement

- Needs: `type`, `risk_level`, `requires_approval`, `evidence`
- Rule:
  - IF `type=action` and (`risk_level=high` OR `requires_approval=true`)
  - THEN `evidence` must contain at least one item
  - otherwise reject with `MISSING_RISK_EVIDENCE`

## Approval Gate

### RULE-GATE-001: Pending Approval Pauses Run

- Needs: `type`, `requires_approval`, `approval.status`
- Rule:
  - IF event indicates pending approval (`approval_requested` or equivalent)
  - THEN projected run status becomes `paused`

### RULE-GATE-002: No Pending Approval Rejection

- Needs: currently pending gate target
- Rule:
  - IF approval resolution is requested for a non-pending target
  - THEN reject with `NO_PENDING_APPROVAL`

### RULE-GATE-003: Duplicate Approval Rejection

- Needs: approval history for target
- Rule:
  - IF target was already resolved
  - THEN reject with `DUPLICATE_APPROVAL`

### RULE-GATE-004: Legal Resolution Transition

- Needs: `approval.status`
- Rule:
  - Legal transition is `pending -> approved|rejected`
  - other transitions reject with `INVALID_APPROVAL_TRANSITION`

### RULE-GATE-005: Rejection Terminal Behavior

- Needs: resolution decision
- Rule:
  - IF approval resolves to `rejected`
  - THEN run projects to rejection/terminal-stop semantics

### RULE-GATE-006: Approved Canonical Demo Orchestration

- Needs: canonical `triage_inbox` run and gate target
- Rule:
  - IF canonical demo gate is approved
  - THEN append explicit continuation receipts (`action`, then terminal
    `summary`)
  - IF continuation append fails
  - THEN return `STORAGE_WRITE_ERROR` and append a fail-loud `error` receipt

### RULE-GATE-007: Approver Requirement

- Needs: `approver_id` on approval API request
- Rule:
  - IF approval resolution request has empty `approver_id`
  - THEN reject with schema validation failure

### RULE-GATE-008: Resolution Timestamp Requirement

- Needs: `approval.resolved_at` on resolved approval events
- Rule:
  - IF resolution event omits `approval.resolved_at`
  - THEN projection fails with `MISSING_APPROVAL_TIMESTAMP`

### RULE-GATE-009: Pending Approvals Deterministic Ordering

- Needs: pending approval projection list
- Rule:
  - Pending approvals are sorted by requested time, then by identifier

### RULE-GATE-010: Summary Completion Requires Closed Approval State

- Needs: `type`, `requires_approval`, `approval.status`, run pending state
- Rule:
  - IF `type=summary`, THEN `requires_approval` must be `false`
  - IF `type=summary`, THEN `approval.status` must be `not_required`
  - IF `type=summary` and run has unresolved pending approval
  - THEN reject with `PENDING_APPROVAL_EXISTS`

## Confidence

### RULE-CONF-001: Confidence Optionality

- Needs: `confidence`
- Rule:
  - `confidence` is optional

### RULE-CONF-002: Confidence Type Validation

- Needs: `confidence`
- Rule:
  - IF `confidence` is not numeric
  - THEN reject with `INVALID_CONFIDENCE_TYPE`

### RULE-CONF-003: Confidence Bounds Validation

- Needs: `confidence`
- Rule:
  - IF `confidence` is outside `0.0..1.0`
  - THEN reject with `INVALID_CONFIDENCE_BOUNDS`

### RULE-CONF-004: Confidence Is Observational

- Needs: `confidence`, `risk_level`
- Rule:
  - Runtime stores provided confidence and risk values as receipts
  - No automatic risk mutation is applied during ingestion

### RULE-CONF-005: Threshold Is Governance Guidance

- Needs: `CONFIDENCE_THRESHOLD`
- Rule:
  - Threshold is guidance for policy authors/reviewers
  - It is not an implicit auto-rewrite rule in current ingestion contract

## Visualization

### RULE-VIS-001: Empty Heatmap

- Needs: projected entries with `risk_level`
- Rule:
  - IF no entries have `risk_level`
  - THEN show empty heatmap state

### RULE-VIS-002: Render Heatmap

- Needs: projected entries with `risk_level`
- Rule:
  - IF entries have risk labels
  - THEN aggregate counts by `risk_level` and render

### RULE-VIS-003: Journal Readability Fields Must Be Present

- Needs: projected journal entry `type`, `title`, `details`
- Rule:
  - IF an event is rendered in the journal timeline
  - THEN `type`, `title`, and `details` must be non-empty strings
  - otherwise projection fails with `MISSING_TIMELINE_FIELDS`

### RULE-VIS-004: Journal Traceability Identity Must Match Source Event

- Needs: stored event identity (`id`, `run_id`) and payload identity
- Rule:
  - IF journal projection renders an event
  - THEN `payload.id` must equal stored event `id`
  - THEN `payload.run_id` must equal stored event `run_id`
  - otherwise projection fails with `TRACEABILITY_LINK_BROKEN`

### RULE-VIS-005: Journal Risky Action Entries Must Include Evidence Links

- Needs: projected journal entry `type`, risk signal, evidence references
- Rule:
  - IF journal entry represents risky `action` (`risk_level=high` OR
    `requires_approval=true`)
  - THEN projected `evidence_refs` must include at least one item
  - otherwise projection fails with `MISSING_RISK_EVIDENCE`
