# 📓 NightLedger Hackathon Diary

This diary tracks our daily progress, architectural findings, and the
implementation journey as we build the "Autonomy with Receipts" accountability
layer.

---

## 🗓️ 2026-02-15: Issue #22 — Run Status Projection (5-Round Big Slik Cycle)

### 🎯 Objective

Ship `GET /v1/runs/:runId/status` as a deterministic, fail-loud projection over
append-only events, with clear structured errors for inconsistent run state.

### 🔁 The 5-Round Process (Human-readable)

### Round 1 — Baseline Delivery

1. **Pattern Investigation:** Reviewed event schema, business rules, and API
   patterns already used in storage/ingest endpoints.
2. **Failing Tests:** Added a dedicated `test_run_status.py` suite covering
   normal flow, pending approvals, resolution outcomes, terminal states, unknown
   run, and inconsistent approval resolution.
3. **Implementation:** Added:
   - `GET /v1/runs/{run_id}/status`
   - Pure projection service `run_status_service.py`
   - Structured errors `RUN_NOT_FOUND` and `INCONSISTENT_RUN_STATE`
   - Exception handlers and presenters
4. **Verification:** New status tests passed, then full suite passed.
5. **Outcome/Learning:** Endpoint worked, but deeper state-machine edge cases
   still needed tightening (found in later rounds).

### Round 2 — Precedence and Terminal Safety Hardening

1. **Pattern Investigation:** Audited Round 1 behavior and found:
   - `approval_resolved` with invalid status could be interpreted as pending.
   - Terminal markers did not block later events.
2. **Failing Tests:** Added tests for:
   - `INVALID_APPROVAL_TRANSITION`
   - `TERMINAL_STATE_CONFLICT`
3. **Implementation:** Reordered projector checks and enforced terminal conflict
   detection.
4. **Verification:** Status suite passed, then full suite passed.
5. **Outcome/Learning:** Projection became strict about invalid resolution
   signals and post-terminal continuation.

### Round 3 — Duplicate Pending Approval Guard

1. **Pattern Investigation:** Found that a second pending approval could
   overwrite the first instead of failing loudly.
2. **Failing Tests:** Added `DUPLICATE_PENDING_APPROVAL` scenario.
3. **Implementation:** Added explicit guard: if pending already exists and
   another pending signal arrives, raise inconsistency.
4. **Verification:** Status suite passed, then full suite passed.
5. **Outcome/Learning:** Prevented silent loss of pending approval context.

### Round 4 — Resolution Metadata Integrity

1. **Pattern Investigation:** Verified approval-resolved events were not
   enforcing required resolver metadata.
2. **Failing Tests:** Added missing-field scenarios for:
   - `MISSING_APPROVER_ID`
   - `MISSING_APPROVAL_TIMESTAMP`
3. **Implementation:** Enforced `approval.resolved_by` and
   `approval.resolved_at` checks in projection path.
4. **Verification:** Status suite passed, then full suite passed.
5. **Outcome/Learning:** Projection now enforces business-rule consistency for
   human decision metadata.

### Round 5 — Rejection Continuation Guard

1. **Pattern Investigation:** Found non-terminal events could continue after a
   rejected approval.
2. **Failing Tests:** Added `REJECTED_STATE_CONFLICT` scenario.
3. **Implementation:** If status is `rejected` and no terminal stop marker
   follows, projection raises inconsistency.
4. **Verification:** Status suite passed, then full suite passed.
5. **Outcome/Learning:** Rejection is now treated as a strict control boundary
   unless explicit stop/terminal semantics follow.

### ✅ Final Audit Summary

- **Docs updated first** for each round in `spec/API.md`.
- **Code touched:** controller endpoint, projection service, error classes,
  presenters, FastAPI handlers.
- **Coverage hardening:** Added explicit storage read error test for status
  endpoint (`STORAGE_READ_ERROR` path).
- **Current result:** `82` tests passing.
- **Deployment readiness decision:** **Ready** for Issue #22 scope. Remaining
  risk is policy semantics for future event types; current MVP status projection
  behavior is deterministic, fail-loud, and fully tested for known edge states.

---

## 🗓️ 2026-02-15: The "Big Slik" Optimization & Protocol

### 🎯 Objectives

- Optimize Event Storage for O(1) performance (Issue #21).
- Finalize Event Payload Validation (Issue #23).
- Ship the "Autonomy with Receipts" foundation.

### ✅ What we shipped

- **Strict TDD & Audit:** Formalized a 5-round TDD process in `agents.md`.
- **High-Performance Storage:** Implemented `InMemoryAppendOnlyEventStore` with
  O(1) lookup for duplicates and run isolation.
- **Data Integrity:** Added deepcopy protections and out-of-order timestamp
  detection (`integrity_warning`).
- **Structured Errors:** Moved from string-based errors to structured
  `DuplicateEventError` and unified validation responses.
- **Full Coverage:** 63 tests passing (100% core logic coverage).

### 💡 Findings & Decisions

- **O(1) vs O(n):** Early on, we were scanning the entire history for
  duplicates. By introducing `_event_id_index` and `_run_records_index`, we
  moved to constant time lookups, which is critical for an append-only ledger
  that grows indefinitely.
- **Immutability:** Even in-memory stores must return deep copies. We found that
  without `deepcopy`, callers could accidentally mutate the "historical record."
- **Code Hygiene Audit:** The 5th round "Sanity Audit" caught unused imports and
  redundant exception catch blocks that 100% test coverage didn't explicitly
  flag.

---

## 🗓️ 2026-02-14: Foundation & Schema

### 🎯 Objectives

- Define the core `EventPayload` schema.
- Implement robust Pydantic-based validation.
- Establish the baseline storage contract.

### ✅ What we shipped

- **Schema v0:** Comprehensive validation for `Actor`, `EventType`, `RiskLevel`,
  and `Approval` states.
- **Ingest Service:** Mapping complex Pydantic errors to user-friendly
  "NightLedger Error Codes."
- **API Spec:** Drafted `spec/API.md` for POST/GET round-trip.

### 💡 Findings & Decisions

- **Timezone Normalization:** Enforcing UTC at the schema level prevents
  "time-travel" bugs in the ledger.
- **Fail Loudly:** Chose `422 Unprocessable Content` with specific codes (e.g.,
  `MISSING_RUN_ID`) over generic 400s to help agent developers debug faster.
