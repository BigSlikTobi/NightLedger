# 📐 NightLedger Business Rules

This document defines the formal business logic for NightLedger. **Source of
Truth:** These rules govern the `Governance Layer` and must be strictly
enforced.

## ID Format

Rules are identified by `RULE-[Category]-[Number]`.

- `RULE-CORE-XXX`: Core data integrity
- `RULE-RISK-XXX`: Risk labeling logic
- `RULE-GATE-XXX`: Approval gate logic
- `RULE-CONF-XXX`: Confidence scoring logic
- `RULE-VIS-XXX`: Visualization logic

---

## 🔴 Core Integrity (APPEND-ONLY)

### RULE-CORE-001: Run ID Requirement

**Context:** Every event must belong to a run.

```
IF run_id is missing
THEN reject event and return error("MISSING_RUN_ID")
```

### RULE-CORE-002: Duplicate Event Prevention

**Context:** Event IDs must be unique within a run.

```
IF event_id is duplicated within run_id
THEN reject event and return error("DUPLICATE_EVENT_ID")
```

### RULE-CORE-003: Timestamp Ordering

**Context:** Time only moves forward.

```
IF timestamp < last_event_timestamp
THEN append event and mark integrity_warning=true
ELSE append event to event_stream and return status("EVENT_INGESTED")
```

---

## 🟡 Risk Labeling

### RULE-RISK-001: Workflow ID Requirement

**Context:** Risk must be associated with a workflow.

```
IF workflow_id is empty
THEN reject event and return error("MISSING_WORKFLOW")
```

### RULE-RISK-002: Default Risk Classification

**Context:** Unknown risks are safe by default but labeled "UNCLASSIFIED".

```
IF risk_category is missing
THEN set risk_category="UNCLASSIFIED" and continue
```

### RULE-RISK-003: Known Risk Identification

**Context:** Only known event types trigger approval events.

```
IF event_type not in risk catalog
THEN set requires_approval=false and attach risk_label="NONE"
ELSE attach risk_label={risk_name,risk_category} and set requires_approval=true
```

---

## 🟠 Approval Gate

### RULE-GATE-001: Risk Pauses Execution

**Context:** A risky event must pause the system.

```
IF requires_approval=true AND workflow_status != "PAUSED"
THEN set workflow_status="PAUSED" and emit approval_request
```

### RULE-GATE-002: No Duplicate Approvals

**Context:** Cannot approve what isn't pending.

```
IF approval submitted AND workflow_status != "PAUSED"
THEN return error("NO_PENDING_APPROVAL")
```

### RULE-GATE-003: Idempotent Approvals

**Context:** Double-clicking approval shouldn't break things.

```
IF approval already resolved
THEN return error("DUPLICATE_APPROVAL")
```

### RULE-GATE-004: Approval Timeout

**Context:** Approvals shouldn't hang forever.

```
IF approval not received within TIMEOUT
THEN set workflow_status="EXPIRED" and emit approval_expired
```

### RULE-GATE-005: Rejection Stops Run

**Context:** "No" means stop.

```
IF approval_status="REJECTED"
THEN set workflow_status="STOPPED" and emit approval_rejected
```

### RULE-GATE-006: Approval Resumes Run

**Context:** "Yes" means go.

```
ELSE set workflow_status="RUNNING" and emit approval_approved
```

---

## 🔵 Confidence Scoring

### RULE-CONF-001: Default Confidence

**Context:** Missing confidence is average.

```
IF confidence_value is missing
THEN set confidence_value=0.5
```

### RULE-CONF-002: Confidence Bounds (Lower)

**Context:** No negative confidence.

```
IF confidence_value < 0
THEN set confidence_value=0
```

### RULE-CONF-003: Confidence Bounds (Upper)

**Context:** No super-confidence.

```
IF confidence_value > 1
THEN set confidence_value=1
```

### RULE-CONF-004: Low Confidence Escalation

**Context:** Being unsure is risky.

```
IF confidence_value < THRESHOLD AND risk_category != "LOW"
THEN escalate risk_category="MEDIUM" and set requires_approval=true
ELSE attach confidence_value and continue
```

---

## 🟢 Visualization

### RULE-VIS-001: Empty Heatmap

**Context:** No data, no map.

```
IF no events have risk_category != "NONE"
THEN show empty_heatmap_state
```

### RULE-VIS-002: Render Heatmap

**Context:** Show the risks.

```
ELSE aggregate risk counts by risk_category (and optionally by time bucket) and render heatmap
```
