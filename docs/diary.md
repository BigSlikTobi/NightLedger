# 📓 NightLedger Hackathon Diary

This diary tracks our daily progress, architectural findings, and the
implementation journey as we build the "Autonomy with Receipts" accountability
layer.

---

# Diary

## 🗓️ 2026-02-15: Issue #31 — Journal Projection Service (5-Round Big Slik Cycle)

### 🎯 Objective

Implement a dedicated representation-layer journal projection service that
transforms ordered `StoredEvent` inputs into deterministic, readable timeline
entries with traceability, evidence, and approval context.

### 🔁 The 5-Round Process (Human-readable)

### Round 1 — Baseline Projection Service

1. **Pattern Investigation:** Confirmed there was no
   `journal_projection_service` and no reusable projection model for the
   journal endpoint.
2. **Failing Tests:** Added `test_round1_project_run_journal_maps_baseline_readable_entry`
   in `tests/test_journal_projection_service.py`.
3. **Implementation:** Added
   `src/nightledger_api/services/journal_projection_service.py` with a pure
   `project_run_journal()` transformation and typed dataclasses.
4. **Verification:** Targeted test passed, then full suite passed.
5. **Outcome/Learning:** Baseline deterministic readable entry mapping and
   payload linkage in place.

### Round 2 — Evidence Traceability

1. **Pattern Investigation:** Baseline output lacked explicit evidence
   references.
2. **Failing Tests:** Added
   `test_round2_project_run_journal_includes_evidence_references`.
3. **Implementation:** Projected `evidence_refs` from source event evidence
   entries in deterministic source order.
4. **Verification:** Targeted test passed, then full suite passed.
5. **Outcome/Learning:** Journal entries now surface evidence pointers directly
   for auditability.

### Round 3 — Approval Transition Visibility

1. **Pattern Investigation:** Approval transitions were present only implicitly
   in `approval_context`.
2. **Failing Tests:** Added
   `test_round3_project_run_journal_surfaces_approval_transition_indicators`.
3. **Implementation:** Added `approval_indicator` projection with:
   `is_approval_required`, `is_approval_resolved`, and `decision`.
4. **Verification:** Targeted test passed, then full suite passed.
5. **Outcome/Learning:** Approval-required and approval-resolved transitions are
   now explicit in projected entries.

### Round 4 — Structured Metadata Projection

1. **Pattern Investigation:** Entry output still lacked a stable metadata block
   for machine-readable context.
2. **Failing Tests:** Added
   `test_round4_project_run_journal_includes_structured_metadata_block`.
3. **Implementation:** Added `metadata` per entry:
   `actor`, `confidence`, `risk_level`, `integrity_warning`.
4. **Verification:** Targeted test passed, then full suite passed.
5. **Outcome/Learning:** Projection schema now contains both narrative fields
   and compact structured context.

### Round 5 — Determinism Guard (Fail Loudly)

1. **Pattern Investigation:** Determinism could drift if callers pass unordered
   event streams.
2. **Failing Tests:** Added
   `test_round5_project_run_journal_fails_loud_on_unordered_input`.
3. **Implementation:** Added explicit unordered input detection and raised
   `InconsistentRunStateError` with code `UNORDERED_EVENT_STREAM`.
4. **Verification:** Targeted test passed, then projector suite passed, then
   full suite passed.
5. **Outcome/Learning:** Projector is now side-effect-free, deterministic, and
   fail-loud on invalid ordering assumptions.

### ✅ Final Audit Summary

- **Docs first:** `docs/ARCHITECTURE.md` updated to declare runtime journal
  projector ownership in the representation layer.
- **Code delivered:** Pure projection service with typed projection models and
  deterministic transformations.
- **Coverage:** Added dedicated projector tests in
  `tests/test_journal_projection_service.py`.
- **Final verification:** `106` tests passing (`./.venv/bin/pytest -q`).
- **Issue #31 readiness decision:** **Ready** for merge; acceptance criteria met
  for deterministic output, traceability, evidence projection, and approval
  transition representation.

## 2026-02-15 — Issue #6 Journal Timeline Refactor (The Big Slik Way)

Today was intense, and honestly useful.

I started by syncing the branch with the latest remote updates and then took
time to understand the current structure before touching anything. The biggest
context changes were your demo-mode integration and the updated `agents.md`
direction in `main`.

I followed the 5-step loop as requested, with practical iterations inside each
step.

### Step 1 — Pattern investigation and scope lock

I reviewed the existing timeline implementation, your new demo-mode flow, and
the repo conventions. I compared branch state against `origin/main`, checked
what had been added, and inspected where the UI currently lived.

Finding: the timeline worked, but it was still plain DOM-string rendering, which
would get harder to maintain once interactions and navigation grow.

Iteration: I decided to move to a framework-based structure while keeping demo
mode and API mode behavior intact.

### Step 2 — Tests first (TDD entry point)

Before the refactor, I rewrote the tests to target a view-model transformation
layer instead of HTML string rendering. This gives us stable tests that focus on
behavior: ordering, risk/approval mapping, and evidence link normalization.

Finding: once tests targeted data-shaping instead of markup details, the
refactor path became safer and cleaner.

Iteration: created failing tests that expected a new `toTimelineCards()` model
function.

### Step 3 — Implementation (minimal code to satisfy tests)

I introduced a new `timeline_model.js` and implemented `toTimelineCards()` with
deterministic sorting and normalized flags/labels. Then I refactored `app.js` to
a Vue 3 app mounted from `index.html`.

Finding: separating model logic from rendering removed most complexity from the
UI component and made state handling straightforward.

Iteration: preserved both runtime paths:

- `runId=demo` uses mock events for local viewing,
- non-demo run IDs call `/v1/runs/:runId/journal`.

### Step 4 — Verification loop

I ran the test suite in `apps/web` and confirmed all tests pass after refactor.
I also re-checked status boundaries manually in code: loading, error, empty, and
success rendering paths.

Finding: the Vue structure now gives us a clean base for future controls
(filters, grouping, timeline navigation, interaction states) without rewriting
architecture later.

Iteration: made small template and mount refinements so the root app container
and rendering flow stay consistent.

### Step 5 — Final audit and hygiene

I aligned documentation and constitution expectations first, then cleaned
accidental tracked artifacts (`__pycache__`, `.pyc`) and hardened `.gitignore`
so this noise won’t reappear.

Findings from audit:

- Documentation needed to explicitly describe frontend representation layering.
- The branch had binary Python cache files that should not be versioned.
- Commit granularity needed to stay atomic and fast.

Iterations completed:

1. docs + constitution alignment,
2. test-first refactor prep,
3. framework migration,
4. artifact cleanup.

Overall progress: strong. The timeline is now in a modern framework, demo mode
remains easy to use, tests validate core behavior, and the branch is cleaner and
easier to evolve.

## 2026-02-15 — MVC follow-up and communication correction

After the first refactor, I received the explicit direction to move the frontend
into an MVC style and to follow the updated `agents.md` from `main` with the
full cycle discipline.

I had a communication gap during execution. That was a process failure on my
side, and I corrected it by resuming with a complete cycle and immediate push.

### Full cycle completed (not just red tests)

1. Goal re-read I re-read the request: keep Vue, but split responsibilities in
   MVC form and preserve demo/runtime behavior.

2. Pattern investigation I inspected `app.js` and identified orchestration logic
   mixed into the view setup. This was the main separation gap.

3. Failing tests I added controller-level tests in `timeline_controller.test.js`
   for two core orchestration behaviors:
   - demo run loads local data and reaches success state,
   - API failure moves state to error with readable message.

4. Minimal implementation I created `timeline_controller.js` and moved
   loading/orchestration logic there. `app.js` now acts as the view binding
   layer and delegates state transitions to the controller.

5. Verification I ran the full web test suite (`npm test` in `apps/web`) and
   confirmed all tests pass, including the new controller tests.

### Findings and iterations

- Finding: framework alone was not enough; orchestration had to be extracted to
  make the architecture truly maintainable.
- Finding: controller tests made state transitions explicit and less fragile.
- Iteration: rebased remote branch updates, resolved script conflicts, reran
  tests, and pushed cleanly.

### Result

The FE now follows a clearer MVC-style split:

- Model: `timeline_model.js`
- Controller: `timeline_controller.js`
- View: Vue app in `app.js`

And the branch includes the incremental commits for test-first controller
introduction, controller integration, and verification.

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
3. **Implementation:** Added resolution history checks before attempting append,
   preserving idempotent behavior for already-resolved targets.
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
  The control surface is deterministic, fail-loud, and fully covered by endpoint
  tests.

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
