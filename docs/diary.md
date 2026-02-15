# 📓 NightLedger Hackathon Diary

This diary tracks our daily progress, architectural findings, and the
implementation journey as we build the "Autonomy with Receipts" accountability
layer.

---

## 🗓️ 2026-02-15: Issue #4 — Approval State Machine + Endpoints (5-Round Big Slik Cycle)

### 🎯 Objective

Ship the human-control surface for risky actions:

- `GET /v1/approvals/pending`
- `POST /v1/approvals/:eventId`

with strict transition rules (`pending -> approved|rejected`) and fail-loud
errors for illegal or stale transitions.

### 🔁 The 5-Round Process (Human-readable)

### Round 1 — Baseline Approval Flow

1. **Pattern Investigation:** Reviewed `spec/API.md`, `spec/BUSINESS_RULES.md`
   and current run-status projection behavior to anchor approval semantics.
2. **Failing Tests:** Added first endpoint tests for:
   - retrieving pending approvals
   - approving a pending request
   - rejecting a pending request
3. **Implementation:** Added `approval_service.py`, wired new controller routes,
   and introduced `list_all()` in the store protocol for cross-run pending
   scans.
4. **Verification:** Ran approvals tests, then full suite.
5. **Outcome/Learning:** Core happy path worked; error semantics still needed
   hardening.

### Round 2 — Illegal Transition Blocking

1. **Pattern Investigation:** Audited edge paths where event IDs are missing,
   duplicated across runs, or target non-pending events.
2. **Failing Tests:** Added explicit cases for:
   - `APPROVAL_NOT_FOUND`
   - `AMBIGUOUS_EVENT_ID`
   - `NO_PENDING_APPROVAL`
3. **Implementation:** Added typed domain errors and route-level exception
   mapping so each illegal transition returns a deterministic code.
4. **Verification:** Re-ran approvals tests and full suite.
5. **Outcome/Learning:** API now blocks illegal transitions with explicit
   machine-readable errors.

### Round 3 — Idempotency + Duplicate Resolution Semantics

1. **Pattern Investigation:** Checked repeated approval calls and stale target
   calls after later approvals appeared in the same run.
2. **Failing Tests:** Added duplicate/stale scenarios requiring
   `DUPLICATE_APPROVAL`.
3. **Implementation:** Added resolution history checks before attempting
   append, preserving idempotent behavior for already-resolved targets.
4. **Verification:** Full suite run after targeted approvals run.
5. **Outcome/Learning:** Duplicate transitions no longer mutate state and now
   fail loudly with consistent error codes.

### Round 4 — Data Integrity + Input Quality

1. **Pattern Investigation:** Audited resolver metadata and request input
   quality (`approver_id`) against business rules.
2. **Failing Tests:** Added coverage for:
   - whitespace-only `approver_id` rejection (`422`)
   - inconsistent run state surfacing through pending endpoint (`409`)
3. **Implementation:** Enforced non-blank `approver_id` using Pydantic
   stripping + `min_length=1` and propagated projection inconsistency instead of
   flattening to generic `500`.
4. **Verification:** Full suite run.
5. **Outcome/Learning:** Input boundaries became strict and inconsistency
   handling stayed transparent.

### Round 5 — Storage Failure + Timestamp Safety

1. **Pattern Investigation:** Audited write-path failure handling and ordering
   risks for synthetic approval resolution events.
2. **Failing Tests:** Added resolution-append failure case expecting
   `STORAGE_WRITE_ERROR`.
3. **Implementation:** Wrapped append failures as `StorageWriteError` and
   guarded `resolved_at` to be strictly after latest run timestamp to avoid
   order collisions.
4. **Verification:** Ran full suite after all fixes.
5. **Outcome/Learning:** Resolution writes are now robust and keep deterministic
   ordering guarantees.

### ✅ Final Audit Summary

- **Docs first:** API contract + error semantics documented in `spec/API.md`,
  and local test instructions added in `docs/API_TESTING.md`.
- **Code delivered:** new approval service, controller routes, store protocol
  extension, typed errors, presenters, and exception handlers.
- **Test status:** `95` tests passing (`./.venv/bin/pytest -q`).
- **Issue #4 deployment-readiness decision:** **Ready** for merge/deploy scope.
  The control surface is deterministic, fail-loud, and fully covered by
  endpoint tests.

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
