# 📓 NightLedger Hackathon Diary

This diary tracks our daily progress, architectural findings, and the
implementation journey as we build the "Autonomy with Receipts" accountability
layer.

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
