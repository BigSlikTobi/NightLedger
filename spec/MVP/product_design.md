# 🌙 NightLedger — Product Design

> Architecture for Accountability by Design

---

## 🧱 Design Integrity Principles

1. Enforcement logic never touches UI layer.
2. UI layer never mutates core event data.
3. Every state transition originates from an event.
4. No silent state changes allowed.
5. Every irreversible action must be interruptible.

---

---

# PART 1 — Universal Schema

## 🧩 Clear Separation of Concerns

NightLedger is built on strict separation between **capture**, **governance**,
and **representation**.

This ensures the system remains:

- Extensible
- Auditable
- Composable
- Predictable

We define **three universal layers**.

---

## 1️⃣ Agent Workflow Integration Layer

### 🎯 Purpose

Integrates external agent workflows into NightLedger. It does **not interpret
decisions** — it captures structured intent only.

### 📦 Responsibilities

- Receive events from agent runtime
- Enforce minimal event schema validation
- Assign `run_id` and `workflow_id`
- Persist append-only event record

### 🧠 Principle

> "Capture first. Interpret later."

This layer never enriches logic. It guarantees structural integrity — nothing
more.

---

## 2️⃣ Workflow Check & Validation Layer

### 🎯 Purpose

Evaluates workflow events against governance rules. Determines whether execution
may continue.

### 📦 Responsibilities

- Detect risky event types
- Evaluate risk category rules
- Validate required fields (evidence, confidence, context)
- Trigger `approval_required` state

### 🧠 Principle

> "Govern before impact."

This is the enforcement engine. It contains **no UI logic**.

---

## 3️⃣ Status Creation & Representation Layer

### 🎯 Purpose

Transforms structured events into human-readable state.

### 📦 Responsibilities

- Project raw events into journal entries
- Create risk labels
- Generate narrative summaries
- Compute trust/confidence signals
- Render timeline states (`running`, `paused`, `approved`, `rejected`,
  `completed`)

### 🧠 Principle

> "Machines write events. Humans read stories."

This layer is responsible for experience — not enforcement.

---

## 🔄 Layer Interaction Diagram

![Layer Interaction Diagram](./flows/layer_interaction.png)

---

# PART 2 — Business Rules

## 📐 Rule Format (Strict)

Every feature defines **exactly one business rule** in this format:

```
IF ... THEN ... ELSE ...
```

If multiple edge cases exist, they are expressed as a prioritized chain:

```
IF ...
ELSE IF ...
ELSE ...
```

---

# 🔴 Feature: Append-only Event Stream

### Required Fields

- `run_id`
- `event_id`
- `timestamp`
- `event_type`

### Edge Cases

- `run_id` missing
- `event_id` duplicated within run
- timestamp out-of-order

### Business Rule

```
IF run_id is missing
THEN reject event and return error("MISSING_RUN_ID")

ELSE IF event_id is duplicated within run_id
THEN reject event and return error("DUPLICATE_EVENT_ID")

ELSE IF timestamp < last_event_timestamp
THEN append event and mark integrity_warning=true

ELSE append event to event_stream and return status("EVENT_INGESTED")
```

---

# 🟡 Feature: Risk Labeling

### Required Fields

- `workflow_id`
- `risk_name`
- `risk_category`
- `event_type`

### Edge Cases

- `workflow_id` empty
- `risk_category` missing
- `event_type` not in risk catalog

### Business Rule

```
IF workflow_id is empty
THEN reject event and return error("MISSING_WORKFLOW")

ELSE IF risk_category is missing
THEN set risk_category="UNCLASSIFIED" and continue

ELSE IF event_type not in risk catalog
THEN set requires_approval=false and attach risk_label="NONE"

ELSE attach risk_label={risk_name,risk_category}
and set requires_approval=true
```

---

# 🟠 Feature: Approval Gate

### Required Fields

- `requires_approval`
- `workflow_status`
- `approval_status` (APPROVED | REJECTED)
- `approver_id`
- `approval_timestamp`

### Edge Cases

- Approval submitted while none pending
- Duplicate approval
- Approval timeout

### Business Rule

```
IF requires_approval=true AND workflow_status != "PAUSED"
THEN set workflow_status="PAUSED" and emit approval_request

ELSE IF approval submitted AND workflow_status != "PAUSED"
THEN return error("NO_PENDING_APPROVAL")

ELSE IF approval already resolved
THEN return error("DUPLICATE_APPROVAL")

ELSE IF approval not received within TIMEOUT
THEN set workflow_status="EXPIRED" and emit approval_expired

ELSE IF approval_status="REJECTED"
THEN set workflow_status="STOPPED" and emit approval_rejected

ELSE set workflow_status="RUNNING" and emit approval_approved
```

---

# 🔵 Feature: Confidence Score

### Required Fields

- `confidence_value` (0..1)
- `risk_category`

### Edge Cases

- Missing value
- Out-of-range value
- Below threshold for non-low risk

### Business Rule

```
IF confidence_value is missing
THEN set confidence_value=0.5

ELSE IF confidence_value < 0
THEN set confidence_value=0

ELSE IF confidence_value > 1
THEN set confidence_value=1

ELSE IF confidence_value < THRESHOLD AND risk_category != "LOW"
THEN escalate risk_category="MEDIUM"
and set requires_approval=true

ELSE attach confidence_value and continue
```

---

# 🟢 Feature: Risk Heatmap Visualization

### Required Fields

- `workflow_id`
- `risk_category` per event
- `timestamp`

### Edge Case

- No risk events exist

### Business Rule

```
IF no events have risk_category != "NONE"
THEN show empty_heatmap_state

ELSE aggregate risk counts by risk_category
(and optionally by time bucket)
and render heatmap
```
