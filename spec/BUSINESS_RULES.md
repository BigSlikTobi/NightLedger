# 📐 NightLedger Business Rules

This document defines the formal business logic for NightLedger. **Source of
Truth:** These rules govern the `Governance Layer` and must be strictly
enforced.

## ID Format

Rules are identified by `RULE-[Category]-[Number]`.

## Field Naming Convention

> [!IMPORTANT]
> The `EVENT_SCHEMA.md` uses short field names (`confidence`, `risk_level`).
> This document uses descriptive names for clarity. The canonical mapping is:
>
> | Schema Field | Business Rules Field | Valid Values               |
> | ------------ | -------------------- | -------------------------- |
> | `confidence` | `confidence`         | `0.0` – `1.0`              |
> | `risk_level` | `risk_level`         | `low`, `medium`, `high`    |
> | `type`       | `event_type`         | See RULE-CORE-005          |
> | `actor`      | `actor`              | `agent`, `system`, `human` |

## Constants

| Constant               | Value | Rationale                               |
| ---------------------- | ----- | --------------------------------------- |
| `CONFIDENCE_THRESHOLD` | `0.4` | Below this, non-low risks are escalated |
| `APPROVAL_TIMEOUT`     | TBD   | Max wait time before expiration         |

---

## 🔴 Core Integrity (APPEND-ONLY)

### RULE-CORE-001: Run ID Requirement

- **Feature:** Event Ingestion
- **Needs:** `run_id` in the event payload
- **Edge Case:** `run_id` is missing
- **Business Rule:**
  ```
  IF run_id is missing
  THEN reject event and return error("MISSING_RUN_ID")
  ELSE process event
  ```

### RULE-CORE-002: Event ID Requirement

- **Feature:** Event Ingestion
- **Needs:** `event_id` in the event payload
- **Edge Case:** `event_id` is missing entirely
- **Business Rule:**
  ```
  IF event_id is missing
  THEN reject event and return error("MISSING_EVENT_ID")
  ELSE process event
  ```

### RULE-CORE-003: Duplicate Event Prevention

- **Feature:** Event Ingestion
- **Needs:** Unique `event_id` within the scope of a `run_id`
- **Edge Case:** `event_id` is duplicated within `run_id`
- **Business Rule:**
  ```
  IF event_id is duplicated within run_id
  THEN reject event and return error("DUPLICATE_EVENT_ID")
  ELSE process event
  ```

### RULE-CORE-004: Timestamp Requirement

- **Feature:** Event Ingestion
- **Needs:** `timestamp` in the event payload
- **Edge Case:** `timestamp` is missing entirely
- **Business Rule:**
  ```
  IF timestamp is missing
  THEN reject event and return error("MISSING_TIMESTAMP")
  ELSE process event
  ```

### RULE-CORE-005: Timestamp Ordering

- **Feature:** Event Stream Consistency
- **Needs:** `timestamp` of current event, `timestamp` of last event
- **Edge Case:** `timestamp` is earlier than `last_event_timestamp`
  (out-of-order)
- **Business Rule:**
  ```
  IF timestamp < last_event_timestamp
  THEN append event and mark integrity_warning=true
  ELSE append event to event_stream and return status("EVENT_INGESTED")
  ```

### RULE-CORE-006: Event Type Requirement

- **Feature:** Event Ingestion
- **Needs:** `event_type` in the event payload
- **Edge Case:** `event_type` is missing
- **Business Rule:**
  ```
  IF event_type is missing
  THEN reject event and return error("MISSING_EVENT_TYPE")
  ELSE process event
  ```

### RULE-CORE-007: Event Type Validation

- **Feature:** Event Ingestion
- **Needs:** `event_type`, list of valid types
  (`intent|action|observation|decision|approval_requested|approval_resolved|error|summary`)
- **Edge Case:** `event_type` is not in the list of valid types
- **Business Rule:**
  ```
  IF event_type not in valid_event_types
  THEN reject event and return error("INVALID_EVENT_TYPE")
  ELSE process event
  ```

### RULE-CORE-008: Actor Validation

- **Feature:** Event Ingestion
- **Needs:** `actor`, list of valid actors (`agent|system|human`)
- **Edge Case:** `actor` is missing or not in the list of valid actors
- **Business Rule:**
  ```
  IF actor is missing OR actor not in valid_actors
  THEN reject event and return error("INVALID_ACTOR")
  ELSE process event
  ```

### RULE-CORE-009: Title and Details Requirement

- **Feature:** Timeline Readability
- **Needs:** `title`, `details`
- **Edge Case:** `title` or `details` is missing
- **Business Rule:**
  ```
  IF title is missing OR details is missing
  THEN reject event and return error("MISSING_TIMELINE_FIELDS")
  ELSE process event
  ```

---

## 🟡 Risk Labeling

### RULE-RISK-001: Workflow ID Requirement

- **Feature:** Risk Assessment
- **Needs:** `workflow_id`
- **Edge Case:** `workflow_id` is empty or missing
- **Business Rule:**
  ```
  IF workflow_id is empty
  THEN reject event and return error("MISSING_WORKFLOW")
  ELSE proceed to risk evaluation
  ```

### RULE-RISK-002: Default Risk Classification

- **Feature:** Risk Assessment
- **Needs:** `risk_level`
- **Edge Case:** `risk_level` is missing in the event data
- **Business Rule:**
  ```
  IF risk_level is missing
  THEN set risk_level="unclassified" and continue
  ELSE use provided risk_level
  ```

### RULE-RISK-003: Risk Name Requirement

- **Feature:** Risk Assessment
- **Needs:** `risk_name`, `risk_level`
- **Edge Case:** `risk_name` is missing when `risk_level` is present and not
  "unclassified"
- **Business Rule:**
  ```
  IF risk_level is present AND risk_level != "unclassified" AND risk_name is missing
  THEN reject event and return error("MISSING_RISK_NAME")
  ELSE process event
  ```

### RULE-RISK-004: Known Risk Identification

- **Feature:** Risk Assessment
- **Needs:** `event_type`, Risk Catalog
- **Edge Case:** `event_type` is NOT in the risk catalog (Unknown/Safe event)
- **Business Rule:**
  ```
  IF event_type not in risk catalog
  THEN set requires_approval=false and attach risk_label="NONE"
  ELSE attach risk_label={risk_name,risk_level} and set requires_approval=true
  ```

---

## 🟠 Approval Gate

### RULE-GATE-001: Risk Pauses Execution

- **Feature:** Execution Governance
- **Needs:** `requires_approval` flag, current `workflow_status`
- **Edge Case:** Event requires approval AND workflow is NOT already paused
- **Business Rule:**
  ```
  IF requires_approval=true AND workflow_status != "PAUSED"
  THEN set workflow_status="PAUSED" and emit approval_request
  ELSE continue execution or maintain paused state
  ```

### RULE-GATE-002: No Duplicate Approvals

- **Feature:** Manual Approval
- **Needs:** `approval_submission`, `workflow_status`
- **Edge Case:** Approval submitted while workflow is RUNNING (not PAUSED)
- **Business Rule:**
  ```
  IF approval submitted AND workflow_status != "PAUSED"
  THEN return error("NO_PENDING_APPROVAL")
  ELSE process approval
  ```

### RULE-GATE-003: Idempotent Approvals

- **Feature:** Manual Approval
- **Needs:** `approval_status`
- **Edge Case:** Approval for this event has already been resolved
- **Business Rule:**
  ```
  IF approval already resolved
  THEN return error("DUPLICATE_APPROVAL")
  ELSE process approval
  ```

### RULE-GATE-004: Approval Timeout

- **Feature:** Manual Approval
- **Needs:** Time elapsed since approval request, `APPROVAL_TIMEOUT` threshold
- **Edge Case:** Approval not received within `APPROVAL_TIMEOUT`
- **Business Rule:**
  ```
  IF approval not received within APPROVAL_TIMEOUT
  THEN set workflow_status="EXPIRED" and emit approval_expired
  ELSE wait for approval
  ```

### RULE-GATE-005: Rejection Stops Run

- **Feature:** Manual Approval
- **Needs:** `approval_status`
- **Edge Case:** `approval_status` is "REJECTED"
- **Business Rule:**
  ```
  IF approval_status="REJECTED"
  THEN set workflow_status="STOPPED" and emit approval_rejected
  ELSE proceed to approval acceptance
  ```

### RULE-GATE-006: Approval Resumes Run

- **Feature:** Manual Approval
- **Needs:** `approval_status`
- **Edge Case:** `approval_status` is "APPROVED"
- **Business Rule:**
  ```
  IF approval_status="APPROVED"
  THEN set workflow_status="RUNNING" and emit approval_approved
  ELSE handling rejection or valid states
  ```

### RULE-GATE-007: Approval State Machine

- **Feature:** Approval Lifecycle
- **Needs:** Current `approval.status`, requested transition
- **Edge Case:** Invalid state transition (e.g., `not_required` → `approved`,
  `rejected` → `approved`)
- **Business Rule:**
  ```
  IF requested transition is not in valid_transitions
  THEN reject and return error("INVALID_APPROVAL_TRANSITION")
  ELSE apply transition
  ```
  Valid transitions: `not_required` → `pending` → `approved|rejected`

### RULE-GATE-008: Approver ID Requirement

- **Feature:** Manual Approval
- **Needs:** `approver_id` (maps to `approval.resolved_by` in schema)
- **Edge Case:** Approval is submitted without an `approver_id`
- **Business Rule:**
  ```
  IF approval submitted AND approver_id is missing
  THEN reject and return error("MISSING_APPROVER_ID")
  ELSE process approval
  ```

### RULE-GATE-009: Approval Timestamp Requirement

- **Feature:** Manual Approval
- **Needs:** `approval_timestamp` (maps to `approval.resolved_at` in schema)
- **Edge Case:** Approval is resolved but `approval_timestamp` is missing
- **Business Rule:**
  ```
  IF approval resolved AND approval_timestamp is missing
  THEN reject and return error("MISSING_APPROVAL_TIMESTAMP")
  ELSE process approval
  ```

---

## 🔵 Confidence Scoring

### RULE-CONF-001: Default Confidence

- **Feature:** Confidence Evaluation
- **Needs:** `confidence`
- **Edge Case:** `confidence` is missing
- **Business Rule:**
  ```
  IF confidence is missing
  THEN set confidence=0.5
  ELSE use provided confidence
  ```

### RULE-CONF-002: Non-Numeric Confidence

- **Feature:** Confidence Evaluation
- **Needs:** `confidence`
- **Edge Case:** `confidence` is not a valid number (string, null, NaN)
- **Business Rule:**
  ```
  IF confidence is not a valid number
  THEN reject event and return error("INVALID_CONFIDENCE_TYPE")
  ELSE process confidence
  ```

### RULE-CONF-003: Confidence Bounds (Lower)

- **Feature:** Confidence Evaluation
- **Needs:** `confidence`
- **Edge Case:** `confidence` < 0
- **Business Rule:**
  ```
  IF confidence < 0
  THEN set confidence=0
  ELSE use provided confidence
  ```

### RULE-CONF-004: Confidence Bounds (Upper)

- **Feature:** Confidence Evaluation
- **Needs:** `confidence`
- **Edge Case:** `confidence` > 1
- **Business Rule:**
  ```
  IF confidence > 1
  THEN set confidence=1
  ELSE use provided confidence
  ```

### RULE-CONF-005: Low Confidence Escalation

- **Feature:** Confidence Evaluation
- **Needs:** `confidence`, `CONFIDENCE_THRESHOLD` (0.4), `risk_level`
- **Edge Case:** Confidence is below threshold AND it is NOT already a minimal
  risk
- **Business Rule:**
  ```
  IF confidence < CONFIDENCE_THRESHOLD AND risk_level != "low"
  THEN escalate risk_level="medium" and set requires_approval=true
  ELSE attach confidence and continue
  ```

---

## 🟢 Visualization

### RULE-VIS-001: Empty Heatmap

- **Feature:** Risk Heatmap
- **Needs:** List of events with risk levels
- **Edge Case:** No events have a risk level other than "NONE"
- **Business Rule:**
  ```
  IF no events have risk_level != "NONE"
  THEN show empty_heatmap_state
  ELSE render heatmap
  ```

### RULE-VIS-002: Render Heatmap

- **Feature:** Risk Heatmap
- **Needs:** List of events with risk levels
- **Edge Case:** Events exist with risk levels (Happy Path/Aggregated View)
- **Business Rule:**
  ```
  IF events exist
  THEN aggregate risk counts by risk_level (and optionally by time bucket) and render heatmap
  ```
