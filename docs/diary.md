# 📓 NightLedger Hackathon Diary

This diary tracks our daily progress, architectural findings, and the
implementation journey as we build the "Autonomy with Receipts" accountability
layer.

---

# Diary

## 🗓️ 2026-02-17: Issue #65 — Approval request validation envelopes (5-Round cycle)

### 🎯 Objective

Normalize request-body validation failures on `POST /v1/approvals/:eventId`
into NightLedger structured error envelopes so downstream handlers receive
deterministic `error.code`, `error.message`, and field-level `error.details`.

### 🔁 The 5-Round Process (Human-readable)

### Round 1 — Contract confirmation and gap isolation

1. **Goal Re-Read:** Confirmed #65 scope is limited to approval request-body
   validation consistency.
2. **Pattern Investigation:** Endpoint used FastAPI default request validation,
   returning framework-native `detail` instead of NightLedger `error` envelope.
3. **Failing Tests:** Strengthened existing whitespace-approver test to assert
   structured envelope shape.
4. **Implementation:** None (test-first round).
5. **Verification:** Targeted tests failed on missing `error` envelope as
   expected.

### Round 2 — Invalid decision envelope contract

1. **Goal Re-Read:** Confirmed deterministic decision-field errors are
   required.
2. **Pattern Investigation:** No test coverage for invalid `decision` enum
   value.
3. **Failing Tests:** Added approval API test asserting `literal_error` maps to
   `INVALID_APPROVAL_DECISION` at path `decision`.
4. **Implementation:** None (test-first round).
5. **Verification:** New test failed with framework-default response body.

### Round 3 — Missing approver envelope contract

1. **Goal Re-Read:** Confirmed approver field-level deterministic codes are
   required.
2. **Pattern Investigation:** Missing `approver_id` path lacked explicit
   structured contract test.
3. **Failing Tests:** Added approval API test asserting missing `approver_id`
   maps to `MISSING_APPROVER_ID`.
4. **Implementation:** None (test-first round).
5. **Verification:** New test failed with framework-default response body.

### Round 4 — Structured validation mapping implementation

1. **Goal Re-Read:** Keep existing approval success/error behavior unchanged
   while normalizing only request validation shape.
2. **Pattern Investigation:** Existing domain error presenters already provide
   deterministic codes and path sorting pattern.
3. **Failing Tests:** Existing Round 1–3 tests remained red.
4. **Implementation:** Added request-validation presenter + endpoint-scoped
   handler in `main.py` for `POST /v1/approvals/:eventId`, mapping decision and
   approver validation errors into NightLedger envelope.
5. **Verification:** `tests/test_approvals_api.py` green.

### Round 5 — Docs + full-suite reconciliation

1. **Goal Re-Read:** Confirmed issue expects canonical envelope behavior
   documented and validated.
2. **Pattern Investigation:** API spec had no structured 422 example for
   approvals request validation.
3. **Failing Tests:** Existing tests enforce envelope behavior for invalid
   approval payloads.
4. **Implementation:** Updated `spec/API.md` with structured validation error
   example; preserved existing approval semantics.
5. **Verification:** Full primary suite green (`155 passed`).

### ✅ Final Audit Summary

- **Goal-vs-implementation check:** #65 acceptance met for structured approval
  payload validation envelopes with deterministic field-level codes.
- **No behavior drift:** Existing approval success/error semantics remain
  unchanged outside request-body validation formatting.
- **Validation evidence:**
  - `./.venv/bin/pytest -q tests/test_approvals_api.py` (`16 passed`)
  - `./.venv/bin/pytest -q tests` (`155 passed`)
## 🗓️ 2026-02-17: Issue #63 — Cleanup: enable real CI checks and fresh-clone bootstrap parity (5-Round cycle)

### 🎯 Objective

Replace placeholder CI behavior with real CI checks for backend and web tests,
and align fresh clone setup docs with the exact commands CI runs.

### 🔁 The 5-Round Process (Human-readable)

### Round 1 — Backend CI regression contract

1. **Goal Re-Read:** Confirmed #63 requires backend regressions to run in CI,
   not placeholder commands.
2. **Pattern Investigation:** `.github/workflows/ci.yml` contained only a
   placeholder echo step and no Python setup.
3. **Failing Tests:** Added
   `test_issue63_round1_ci_runs_backend_regression_suite_with_deterministic_python_setup`.
4. **Implementation:** Added `actions/setup-python@v5`, Python 3.11 pin,
   project `.venv` creation, dependency install, and `./.venv/bin/pytest -q`.
5. **Verification:** Round test passed.

### Round 2 — Web CI regression contract

1. **Goal Re-Read:** Confirmed #63 requires web test execution in CI.
2. **Pattern Investigation:** No Node/Web test job existed in workflow.
3. **Failing Tests:** Added `test_issue63_round2_ci_runs_web_test_command`.
4. **Implementation:** Added `web-tests` job with Node 20 setup and
   `node --test model/*.test.js controller/*.test.js` in `apps/web`.
5. **Verification:** Round test and web tests passed.

### Round 3 — Placeholder removal + trigger integrity

1. **Goal Re-Read:** Confirmed acceptance requires CI to no longer be
   placeholder-only.
2. **Pattern Investigation:** Verified workflow trigger/job structure and
   encoded placeholder-removal checks.
3. **Failing Tests:** Added
   `test_issue63_round3_ci_is_not_placeholder_only_and_runs_on_push_and_pr`.
4. **Implementation:** Existing Round 1/2 workflow changes already satisfied
   the contract; no additional code path was required.
5. **Verification:** Round test passed.

### Round 4 — Canonical local verification docs parity

1. **Goal Re-Read:** Confirmed #63 requires one canonical local verification
   command flow matching CI.
2. **Pattern Investigation:** Root README still referenced outdated `pnpm`
   bootstrap and did not match actual stack checks.
3. **Failing Tests:** Added
   `test_issue63_round4_readme_documents_canonical_local_verification_flow_matching_ci`.
4. **Implementation:** Replaced root quick start with fresh clone Python setup
   and added `Local Verification (Matches CI)` section including backend and
   web commands.
5. **Verification:** Round test passed.

### Round 5 — Mandatory diary completion

1. **Goal Re-Read:** Confirmed diary updates are mandatory on issue completion.
2. **Pattern Investigation:** No `Issue #63` diary record existed.
3. **Failing Tests:** Added
   `test_issue63_round5_diary_records_ci_and_fresh_clone_bootstrap_parity_work`.
4. **Implementation:** Added this entry documenting the real CI checks and
   fresh clone alignment.
5. **Verification:** Round test passed.

### ✅ Final Audit Summary

- **Goal-vs-implementation check:** #63 acceptance criteria met:
  - CI now runs backend regressions with deterministic Python setup.
  - CI runs web regressions via Node test command.
  - Placeholder-only CI behavior removed.
  - Root docs now provide one canonical local verification flow matching CI.
- **Validation evidence (this worktree):**
  - `./.venv/bin/pytest -q tests/test_issue63_ci_bootstrap_docs.py` (`5 passed`)
  - `node --test model/*.test.js controller/*.test.js` (`18 passed`)
- **Known local verification gap:** full Python suite run
  (`./.venv/bin/pytest -q`) is currently blocked in this sandbox because
  `httpx` cannot be fetched from network-restricted pip mirrors. CI on GitHub
  should resolve this by installing dependencies from `requirements.txt`.

### Issue #63 follow-up — CI compatibility hotfix (2026-02-17)

- **Finding:** GitHub CI reported `23` failures due
  `AttributeError: module 'starlette.status' has no attribute 'HTTP_422_UNPROCESSABLE_CONTENT'`.
- **Fix:** Added a compatibility constant in
  `src/nightledger_api/main.py`:
  `SCHEMA_VALIDATION_STATUS_CODE = getattr(status, "HTTP_422_UNPROCESSABLE_CONTENT", 422)`
  and routed schema-validation responses through that constant.
- **Regression test:** Added `tests/test_status_code_compat.py` to enforce
  status constant compatibility across Starlette/FastAPI versions.
- **Verification:** 
  - `./.venv/bin/pytest -q tests/test_status_code_compat.py` (`1 passed`)
  - `./.venv/bin/pytest -q tests/test_demo_script_issue54_docs.py tests/test_demo_setup_docs.py tests/test_journal_contract_docs.py tests/test_web_live_mode_docs.py tests/test_journal_projection.py tests/test_journal_projection_service.py` (`32 passed`)

## 🗓️ 2026-02-16: Issue #59 — Web UI live API mode (base URL + run selection UX) (5-Round cycle)

### 🎯 Objective

Remove local/dev friction for live UI usage by adding explicit runtime mode/API
base behavior, cross-origin readiness, and operator-ready docs for running UI
and API on separate ports.

### 🔁 The 5-Round Process (Human-readable)

### Round 1 — Runtime mode/base strategy contract

1. **Goal Re-Read:** Confirmed issue requires deterministic live-vs-demo mode
   handling and API base fallback behavior.
2. **Pattern Investigation:** `app.js` inferred demo from `runId` only and had
   no explicit runtime config boundary.
3. **Failing Tests:** Added
   `apps/web/controller/runtime_config.test.js` for default demo and non-demo
   run live fallback behavior.
4. **Implementation:** Added
   `apps/web/controller/runtime_config.js` with deterministic resolution.
5. **Verification:** Full suites green.

### Round 2 — Explicit API client boundary with live base URL support

1. **Goal Re-Read:** Confirmed UI must call live backend reliably across
   origin/port splits.
2. **Pattern Investigation:** API calls were scattered in `app.js` with relative
   paths, causing local cross-port mismatches.
3. **Failing Tests:** Added
   `apps/web/controller/api_client.test.js` for URL composition with/without
   `apiBase`.
4. **Implementation:** Added `apps/web/controller/api_client.js` and rewired
   `apps/web/view/app.js` to consume runtime config + API client boundary.
5. **Verification:** Full suites green.

### Round 3 — Intentional live-mode selection fallback

1. **Goal Re-Read:** Confirmed live mode must be explicit and easy to enter.
2. **Pattern Investigation:** `mode=live` without `runId` still resolved to
   `runId=demo`, causing a non-obvious live failure path.
3. **Failing Tests:** Added runtime-config test for
   `mode=live` with canonical run fallback.
4. **Implementation:** Added canonical live run fallback to
   `run_triage_inbox_demo_1` when live mode is explicit and `runId` is missing.
5. **Verification:** Full suites green.

### Round 4 — Copy-paste live UI+API operator flow docs

1. **Goal Re-Read:** Confirmed issue acceptance requires explicit local run docs
   for live UI + API.
2. **Pattern Investigation:** Web README lacked a concrete two-terminal command
   path and parameterized URL example.
3. **Failing Tests:** Added
   `tests/test_web_live_mode_docs.py::test_issue59_round4_web_readme_includes_copy_paste_live_mode_run_flow`.
4. **Implementation:** Added `Live Mode (UI + API)` section in
   `apps/web/README.md` with copy-paste commands and URL parameters.
5. **Verification:** Full suites green.

### Round 5 — Cross-origin browser readiness (CORS)

1. **Goal Re-Read:** Confirmed acceptance includes separate origin/port support.
2. **Pattern Investigation:** API preflight returned `405`; UI at `3000` could
   not reliably call API at `8001` in browser.
3. **Failing Tests:** Added
   `tests/test_cors_live_ui.py::test_issue59_round5_cors_preflight_allows_local_web_origin`.
4. **Implementation:** Added FastAPI `CORSMiddleware` in
   `src/nightledger_api/main.py` for standard local web origins.
5. **Verification:** Full suites green.

### ✅ Final Audit Summary

- **Goal-vs-implementation check:** Issue #59 acceptance criteria met:
  - live UI can target backend across different local origins/ports
  - approval resolution path refreshes live timeline + pending state
  - demo mode remains intentionally selectable
  - docs include copy-paste live UI+API run flow
  - tests cover runtime mode + API base behavior and CORS readiness
- **Code hygiene:** Introduced explicit API client/runtime boundaries for UI,
  preserved representation-only responsibilities in frontend, and kept
  governance logic in backend services.
- **Validation evidence:**
  - `./.venv/bin/pytest -q` (`150 passed`)
  - `npm --prefix apps/web test` (`16 passed`)

### Follow-up Observability Hardening (Issue #59 continuation)

1. Added explicit UI approval lifecycle console logs in
   `apps/web/view/app.js` and `apps/web/controller/timeline_controller.js`:
   - `approval_decision_requested`
   - `approval_decision_completed`
   - `approval_decision_failed`
2. Added structured backend approval resolution logs to both module logger and
   `uvicorn.error`, including decision and approver metadata:
   - `approval_resolution_requested`
   - `approval_resolution_completed`
   - `approval_resolution_failed`
3. Expanded tests for frontend and API logging behavior, including a regression
   check that `uvicorn.error` receives structured completion logs.
4. Updated docs:
   - `apps/web/README.md` browser observability notes
   - `docs/API_TESTING.md` expected structured terminal log markers
5. Verification:
   - `./.venv/bin/pytest -q` (`153 passed`)
   - `npm --prefix apps/web test` (`18 passed`)

## 🗓️ 2026-02-16: Issue #54 — Reproducible demo script and operator handoff (5-Round cycle)

### 🎯 Objective

Finalize the ship-gate handoff by making `docs/DEMO_SCRIPT.md` reproducible for
another teammate, with explicit outputs, troubleshooting, and evidence mapping.

### 🔁 The 5-Round Process (Human-readable)

### Round 1 — Reproducible command path + expected outputs

1. **Goal Re-Read:** Confirmed #54 requires reproducibility from docs only.
2. **Pattern Investigation:** Existing script was narrative-heavy and lacked one
   canonical `triage_inbox` command path with concrete expected outputs.
3. **Failing Tests:** Added
   `test_issue54_round1_demo_script_defines_reproducible_command_path_with_expected_outputs`.
4. **Implementation:** Rewrote demo script around canonical flow:
   seed -> paused -> approve -> completed, with expected outputs per step.
5. **Verification:** Full suites green after restoring prior journal-doc
   compatibility expectations.

### Round 2 — Troubleshooting matrix for operator recovery

1. **Goal Re-Read:** Confirmed handoff requires reliable recovery, not only
   happy path steps.
2. **Pattern Investigation:** No structured troubleshooting section existed.
3. **Failing Tests:** Added
   `test_issue54_round2_demo_script_includes_troubleshooting_matrix`.
4. **Implementation:** Added `Troubleshooting` with failure signatures and
   checks for API readiness, `NO_PENDING_APPROVAL`, and `RUN_NOT_FOUND`.
5. **Verification:** Full suites green.

### Round 3 — Step-to-receipt evidence checklist

1. **Goal Re-Read:** Confirmed issue requires explicit evidence mapping.
2. **Pattern Investigation:** Script lacked a single checklist mapping steps to
   journal/event receipts.
3. **Failing Tests:** Added
   `test_issue54_round3_demo_script_contains_step_to_receipt_evidence_checklist`.
4. **Implementation:** Added `Evidence Checklist` table linking each step to
   auditable receipts (`approval_requested`, `approval_resolved`,
   `evt_triage_inbox_004`, `evt_triage_inbox_005`).
5. **Verification:** Full suites green.

### Round 4 — Operator handoff gate criteria

1. **Goal Re-Read:** Confirmed teammate handoff needs clear go/no-go criteria.
2. **Pattern Investigation:** No operator signoff section existed.
3. **Failing Tests:** Added
   `test_issue54_round4_demo_script_contains_operator_handoff_gates`.
4. **Implementation:** Added `Operator Handoff` section with teammate execution
   checklist and `Go/No-Go` gates (`run_status`, orchestration, timing target).
5. **Verification:** Full suites green.

### Round 5 — Diary completion requirement

1. **Goal Re-Read:** Confirmed diary update is mandatory for completed issue
   work.
2. **Pattern Investigation:** No `Issue #54` diary entry existed.
3. **Failing Tests:** Added
   `test_issue54_round5_diary_records_demo_script_handoff_completion`.
4. **Implementation:** Added this issue-completion entry with implementation and
   validation evidence.
5. **Verification:** Full suites green.

### ✅ Final Audit Summary

- **Goal-vs-implementation check:** #54 acceptance criteria met:
  - demo is reproducible from docs with canonical command path
  - expected outputs are explicit at each gate
  - evidence mapping is complete and step-linked
  - operator troubleshooting + go/no-go handoff provided
  - diary entry captured with validation evidence
- **Validation evidence:**
  - `./.venv/bin/pytest -q` (`146 passed`)
  - `npm --prefix apps/web test` (`10 passed`)

## 🗓️ 2026-02-16: Issue #54 follow-up — persistent API command-path hardening

### 🎯 Objective

Close a reproducibility gap found during the parent issue #8 audit where
`reset_seed_triage_inbox_demo.sh` auto-start mode terminated the API process at
script exit before subsequent demo curl steps.

### What was changed

- Added a new docs contract test:
  `test_issue54_round6_demo_script_uses_persistent_api_then_seed_without_auto_start`.
- Updated `docs/DEMO_SCRIPT.md` command path to:
  - start API in a persistent terminal (`uvicorn`)
  - run seeding with `AUTO_START=0` in a second terminal
- Preserved existing evidence, troubleshooting, and handoff sections.

### Validation

- `./.venv/bin/pytest -q` (`148 passed`)
- `npm --prefix apps/web test` (`10 passed`)

## 🗓️ 2026-02-16: Issue #53 follow-up — SOTA hardening pass

### 🎯 Objective

Apply post-audit hardening for timing precision, test stability, and
verification-artifact maintainability.

### What was changed

- Updated approval timing calculation in
  `src/nightledger_api/services/approval_service.py` to use conservative
  millisecond ceiling via `_elapsed_ms_ceiling`, preventing boundary
  under-reporting.
- Strengthened timing tests in
  `tests/test_triage_inbox_orchestration_api.py`:
  - removed brittle assumption that `within_target` is always `true`
  - added deterministic rounding test using patched monotonic timer ticks to
    prove `1000.1ms -> 1001ms` and `within_target=false`
- Strengthened artifact governance in
  `docs/artifacts/issue-53/triage_inbox_verification.md` by adding explicit
  contract assertions and regeneration commands.
- Added docs guardrail test in `tests/test_demo_setup_docs.py` to enforce the
  presence of contract assertions + refresh path.
- Updated timing semantics docs in `spec/API.md` and verification expectations
  in `docs/API_TESTING.md`.

### Validation

- `./.venv/bin/pytest -q` (`142 passed`)
- `npm --prefix apps/web test` (`10 passed`)

## 🗓️ 2026-02-16: Issue #53 — Integration demo end-to-end verification + MVP timing checks (5-Round cycle)

### 🎯 Objective

Add explicit, testable verification for the `triage_inbox` end-to-end approval
flow, validate approval-to-state-update MVP timing behavior, and publish
reviewable verification artifacts.

### 🔁 The 5-Round Process (Human-readable)

### Round 1 — API timing receipt contract

1. **Goal Re-Read:** Confirmed #53 requires objective timing verification, not
   implicit assumptions.
2. **Pattern Investigation:** Approval API response exposed orchestration and
   status but had no explicit timing receipt.
3. **Failing Tests:** Added
   `test_issue53_round1_approval_resolution_reports_mvp_timing_receipt`.
4. **Implementation:** Added `timing` block to approval-resolution response:
   `target_ms`, `approval_to_state_update_ms`, `within_target`; updated
   `spec/API.md` and `docs/API_TESTING.md` first.
5. **Verification:** Full suite green (`136 passed` + web tests passing).

### Round 2 — Deterministic orchestration timing gap

1. **Goal Re-Read:** Confirmed timing evidence must prove transition behavior
   in append-only receipts, not only request runtime.
2. **Pattern Investigation:** No explicit value exposed for deterministic gap
   between `approval_resolved` and terminal orchestration receipt.
3. **Failing Tests:** Added
   `test_issue53_round2_triage_inbox_reports_deterministic_orchestration_gap`.
4. **Implementation:** Added
   `timing.orchestration_receipt_gap_ms` (canonical `triage_inbox` flow => `2`
   ms; otherwise `null`) and documented contract updates.
5. **Verification:** Full suite green (`137 passed` + web tests passing).

### Round 3 — Explicit transition semantics in timing receipt

1. **Goal Re-Read:** Confirmed verification should be operator-readable without
   inferring state changes from multiple fields.
2. **Pattern Investigation:** Timing block lacked explicit source/target state
   transition.
3. **Failing Tests:** Added
   `test_issue53_round3_timing_receipt_reports_state_transition`.
4. **Implementation:** Added `timing.state_transition` (for example
   `paused->completed`) and updated API docs/testing guide first.
5. **Verification:** Full suite green (`138 passed` + web tests passing).

### Round 4 — Artifact path contract in operator docs

1. **Goal Re-Read:** Confirmed issue acceptance requires artifacts/logs to be
   available for review.
2. **Pattern Investigation:** Docs had no canonical location for verification
   artifacts.
3. **Failing Tests:** Added
   `test_issue53_round4_api_testing_docs_reference_integration_artifact_path`.
4. **Implementation:** Added
   `Integration verification artifacts (Issue #53)` section in
   `docs/API_TESTING.md` with canonical artifact path.
5. **Verification:** Full suite green (`139 passed` + web tests passing).

### Round 5 — Committed verification artifact content

1. **Goal Re-Read:** Confirmed artifacts must contain concrete proof, not just
   a placeholder path.
2. **Pattern Investigation:** Artifact file did not yet exist.
3. **Failing Tests:** Added
   `test_issue53_round5_verification_artifact_contains_timing_and_state_proof`.
4. **Implementation:** Added
   `docs/artifacts/issue-53/triage_inbox_verification.md` with captured
   reset/pause/approve/completed evidence and timing receipt values.
5. **Verification:** Full suite green (`140 passed` + web tests passing).

### ✅ Final Audit Summary

- **Goal-vs-implementation check:** #53 acceptance criteria met:
  - end-to-end `triage_inbox` integration verification is explicit and tested
  - approval update timing is validated against MVP target contract
  - full backend + web suites pass without regressions
  - reviewable artifact/log output is committed and linked in docs
- **Code hygiene:** tightened test assertions to allow additive contract
  evolution, kept orchestration/timing logic in governance services only,
  preserved UI separation.
- **Validation evidence:**
  - `./.venv/bin/pytest -q` (`140 passed`)
  - `npm --prefix apps/web test` (`10 passed`)

## 🗓️ 2026-02-16: Issue #51 — Integration demo backend triage_inbox orchestration + approval pause/resume (5-Round cycle)

### 🎯 Objective

Wire backend orchestration for the deterministic `triage_inbox` demo so risky
steps pause, approvals resume safely to completion, transitions are explicitly
queryable, and failure paths are fail-loud with receipts.

### 🔁 The 5-Round Process (Human-readable)

### Round 1 — Approved triage gate reaches terminal completion

1. **Goal Re-Read:** Confirmed #51 requires pause on risky step and resume to terminal completion.
2. **Pattern Investigation:** Existing flow stopped at `approved`; no completion orchestration existed.
3. **Failing Tests:** Added `test_round1_triage_inbox_approval_resume_reaches_terminal_completed_state`.
4. **Implementation:** Extended approval service to append deterministic
   post-approval `action` (`evt_triage_inbox_004`) and terminal `summary`
   (`evt_triage_inbox_005`) for seeded demo flow.
5. **Verification:** Full suite green (`132 passed`).

### Round 2 — Response-level transition queryability

1. **Goal Re-Read:** Confirmed transition state must be explicit and queryable.
2. **Pattern Investigation:** Approval API response lacked resulting run state
   and orchestration receipt metadata.
3. **Failing Tests:** Added `test_round2_triage_inbox_approval_response_surfaces_transition_receipts`.
4. **Implementation:** Added `run_status` and `orchestration` block to
   approval-resolution response.
5. **Verification:** Full suite green (`133 passed`).

### Round 3 — Fail-loud + journaled orchestration failure path

1. **Goal Re-Read:** Confirmed no-silent-failure requirement and auditable error paths.
2. **Pattern Investigation:** Orchestration append failure returned `500` but
   left no explicit error receipt in run journal.
3. **Failing Tests:** Added
   `test_round3_orchestration_append_failure_is_structured_and_journaled`.
4. **Implementation:** On orchestration append failure, service now best-effort
   appends a terminal `error` event (`meta.step: run_stopped`) and re-raises
   `StorageWriteError`.
5. **Verification:** Full suite green (`134 passed`).

### Round 4 — Explicit storage error detail contract

1. **Goal Re-Read:** Confirmed error path should be structured and explicit.
2. **Pattern Investigation:** Storage error message was generic
   (`storage backend append failed`).
3. **Failing Tests:** Tightened Round 3 test to assert explicit orchestration
   failure detail message.
4. **Implementation:** Raised
   `StorageWriteError("triage_inbox orchestration append failed")` for
   continuation write failures.
5. **Verification:** Full suite green (`134 passed`).

### Round 5 — Canonical target guard for orchestration scope

1. **Goal Re-Read:** Confirmed orchestration should be deterministic and avoid
   side effects outside intended demo gate.
2. **Pattern Investigation:** Orchestration was keyed only by run ID, so any
   approved pending event in the demo run triggered completion writes.
3. **Failing Tests:** Added
   `test_round5_orchestration_applies_only_to_canonical_triage_demo_approval`.
4. **Implementation:** Scoped orchestration to canonical seeded target
   `evt_triage_inbox_003` in `run_triage_inbox_demo_1`.
5. **Verification:** Full suite green (`135 passed`).

### ✅ Final Audit Summary

- **Goal-vs-implementation check:** #51 acceptance criteria met:
  - risky gate pauses (`paused` before approval)
  - approval resumes to terminal completion for canonical demo flow
  - transitions are explicit/queryable (`run_status`, `orchestration`,
    journal/event receipts)
  - failure paths are structured and fail-loud with journaled error receipts
- **Code hygiene:** Added focused tests and isolated service-layer changes only;
  no UI/governance boundary violations.
- **Validation evidence:**
  - `./.venv/bin/pytest -q` (final: `135 passed`)

## 🗓️ 2026-02-16: Approval stale-target duplicate fix follow-up

### 🎯 Objective

Fix failing approval API behavior where resolving a previously resolved target
after a new pending event in the same run returned `INCONSISTENT_RUN_STATE`
instead of `DUPLICATE_APPROVAL`.

### What was changed

- Updated duplicate-resolution detection in
   `src/nightledger_api/services/approval_service.py` to reliably identify prior
   resolution by matching generated resolution event IDs using the
   `apr_<target_event_id>_...` prefix.

### Validation

- `./.venv/bin/pytest -q tests/test_approvals_api.py::test_post_approval_returns_duplicate_for_stale_resolved_target_with_new_pending`
- `./.venv/bin/pytest -q`

### Result

- Stale resolved targets now consistently return `DUPLICATE_APPROVAL`.
- Full suite is green (`131 passed`).

## 🗓️ 2026-02-16: Issue #50 — Deterministic triage_inbox fixture + reset path (5-Round restart)

### 🎯 Objective

Deliver a deterministic `triage_inbox` reset/seed path with a one-command setup
flow, schema-validated seed data, and fail-loud setup behavior.

### 🔁 The 5-Round Process (Human-readable)

### Round 1 — Deterministic reset/seed API contract

1. **Goal Re-Read:** Confirmed issue #50 requires deterministic seed + reset baseline.
2. **Pattern Investigation:** Found no dedicated `reset-seed` endpoint.
3. **Failing Tests:** Added
   `test_round1_demo_reset_seed_returns_deterministic_manifest` and confirmed
   red (`404`).
4. **Implementation:** Added `POST /v1/demo/triage_inbox/reset-seed` with fixed
   payload fixture and deterministic manifest response.
5. **Verification:** Round test green; full suite run executed (single unrelated
   pre-existing approvals failure remained).

### Round 2 — One-command setup path

1. **Goal Re-Read:** Confirmed issue requires one command for local setup.
2. **Pattern Investigation:** No script existed under `tasks/`.
3. **Failing Tests:** Added
   `test_round2_single_command_setup_script_exists_and_is_executable` and
   confirmed red.
4. **Implementation:** Added executable
   `tasks/reset_seed_triage_inbox_demo.sh` with optional API auto-start and
   seed endpoint call.
5. **Verification:** Round test green; full suite run executed (same unrelated
   approvals failure).

### Round 3 — Structured setup failure logging

1. **Goal Re-Read:** Confirmed no-silent-failure requirement from constitution.
2. **Pattern Investigation:** Seed path had no structured failure logs.
3. **Failing Tests:** Added
   `test_round3_logs_structured_setup_failure` and confirmed red.
4. **Implementation:** Added structured `demo_seed_failed` logging with event
   IDs, error class, and message.
5. **Verification:** Round test green; full suite run executed (same unrelated
   approvals failure).

### Round 4 — Structured error envelope for unexpected append failures

1. **Goal Re-Read:** Confirmed setup failures must remain structured and visible.
2. **Pattern Investigation:** Unexpected append exceptions surfaced as raw
   runtime failures.
3. **Failing Tests:** Added
   `test_round4_unexpected_seed_append_failure_returns_structured_storage_error`
   and confirmed red.
4. **Implementation:** Wrapped unexpected seed failures into
   `StorageWriteError("demo reset-seed failed")` while preserving schema and
   duplicate error semantics.
5. **Verification:** Round tests green; full suite run executed (same unrelated
   approvals failure).

### Round 5 — API runbook enforces single-command setup

1. **Goal Re-Read:** Confirmed reproducibility requirement for another teammate.
2. **Pattern Investigation:** `docs/API_TESTING.md` still used raw curl path.
3. **Failing Tests:** Added
   `test_round5_api_testing_docs_include_single_command_demo_setup` and
   confirmed red.
4. **Implementation:** Updated docs to standardize on
   `bash tasks/reset_seed_triage_inbox_demo.sh`.
5. **Verification:** Round docs test green; full suite run executed (same
   unrelated approvals failure).

### ✅ Final Audit Summary

- **Goal-vs-implementation check:**
  - deterministic reset/seed API endpoint delivered
  - one-command setup path delivered
  - schema validation enforced during seed
  - setup failure logging and structured error envelope behavior delivered
- **Code hygiene:** no additional unrelated refactors introduced.
- **Verification evidence:**
  - `./.venv/bin/pytest -q tests/test_demo_setup_api.py`
  - `./.venv/bin/pytest -q tests/test_demo_setup_docs.py`
  - `./.venv/bin/pytest -q` (single pre-existing unrelated approval test failure persists)


## 🗓️ 2026-02-15: Issue #34 — Journal API Integration Coverage (5-Round Big Slik Cycle)

### 🎯 Objective

Lock `GET /v1/runs/{run_id}/journal` behavior at the HTTP boundary with
integration tests for happy path, deterministic ordering, and fail-loud error
envelopes.

### 🔁 The 5-Round Process (Human-readable)

### Round 1 — Approval Timeline Inconsistency at API Boundary

1. **Pattern Investigation:** Existing tests covered malformed payload/timestamp
   inconsistency, but not approval timeline inconsistency projected through the
   endpoint.
2. **Failing Tests:** Added
   `test_issue34_round1_get_run_journal_surfaces_approval_timeline_inconsistency`
   in `tests/test_journal_api.py`.
3. **Implementation:** Added approval timeline consistency guard in journal
   route by reusing `project_run_status(events)` before returning projection.
4. **Verification:** Targeted round test passed, then full suite passed.
5. **Outcome/Learning:** Journal endpoint now surfaces approval state-machine
   inconsistencies as `409 INCONSISTENT_RUN_STATE`.

### Round 2 — Deterministic Order with Realistic Run Data

1. **Pattern Investigation:** Happy-path test only covered one event and did
   not prove deterministic order on realistic approval flow data.
2. **Failing Tests:** Added
   `test_issue34_round2_get_run_journal_is_deterministically_ordered_for_realistic_run`.
3. **Implementation:** Test-only hardening; endpoint behavior already satisfied
   ordering contract.
4. **Verification:** Targeted round test passed, then full suite passed.
5. **Outcome/Learning:** Ordering is now explicitly locked for out-of-order
   ingestion scenarios at the HTTP layer.

### Round 3 — Full Unknown-Run Envelope Contract

1. **Pattern Investigation:** Unknown-run assertions were partial (`code/path`)
   and could miss envelope drift.
2. **Failing Tests:** Added
   `test_issue34_round3_get_run_journal_unknown_run_uses_full_error_envelope`.
3. **Implementation:** Test-only hardening; behavior already matched contract.
4. **Verification:** Targeted round test passed, then full suite passed.
5. **Outcome/Learning:** Unknown-run error envelope is now guarded end-to-end
   (status, message, path, type, code).

### Round 4 — Full Storage Failure Envelope Contract

1. **Pattern Investigation:** Storage-read failure assertions were also partial.
2. **Failing Tests:** Added
   `test_issue34_round4_get_run_journal_storage_failure_uses_full_error_envelope`.
3. **Implementation:** Test-only hardening; behavior already matched contract.
4. **Verification:** Targeted round test passed, then full suite passed.
5. **Outcome/Learning:** `500 STORAGE_READ_ERROR` envelope is now fully locked.

### Round 5 — Full Inconsistent-State Envelope Contract

1. **Pattern Investigation:** Inconsistency tests did not assert complete error
   envelope semantics for approval timeline failures.
2. **Failing Tests:** Added
   `test_issue34_round5_get_run_journal_inconsistency_uses_full_error_envelope`.
3. **Implementation:** Test-only hardening; behavior already matched contract
   after Round 1 wiring change.
4. **Verification:** `tests/test_journal_api.py` passed end-to-end, then full
   suite passed.
5. **Outcome/Learning:** `409 INCONSISTENT_RUN_STATE` envelope contract is now
   explicitly protected against regression.

### ✅ Final Audit Summary

- **HTTP coverage expanded:** journal endpoint integration tests now include
  realistic deterministic ordering and full envelope assertions for all key
  failure modes.
- **Controller hardening delivered:** journal endpoint now reuses status
  projection to fail loud on approval timeline inconsistencies.
- **Validation completed:**
  - `./.venv/bin/pytest -q tests/test_journal_api.py`
  - `./.venv/bin/pytest -q`
- **Final verification:** `126` tests passing.
- **Issue #34 readiness decision:** **Ready** for merge; API boundary contract
  coverage is complete and stable.

## 🗓️ 2026-02-15: Issue #35 — Journal Endpoint Usage Docs (5-Round Big Slik Cycle)

### 🎯 Objective

Document practical usage of `GET /v1/runs/{run_id}/journal` in local API testing
and demo operations, with explicit readability and evidence-traceability
guidance that matches implemented contract semantics.

### 🔁 The 5-Round Process (Human-readable)

### Round 1 — API Testing Flow Coverage

1. **Pattern Investigation:** `docs/API_TESTING.md` covered approval APIs but
   had no runnable journal endpoint flow.
2. **Failing Tests:** Added
   `test_round1_api_testing_docs_include_journal_endpoint_curl_flow` to
   `tests/test_journal_contract_docs.py`.
3. **Implementation:** Added `Journal Endpoint Smoke Flow (Issue #35)` with
   runnable curl commands for known and unknown runs.
4. **Verification:** Targeted docs contract test passed after doc update.
5. **Outcome/Learning:** Operator docs now include direct runbook commands for
   journal projection checks.

### Round 2 — Response Field Contract Clarity

1. **Pattern Investigation:** API testing guide did not explain projected entry
   field semantics.
2. **Failing Tests:** Added
   `test_round2_api_testing_docs_define_journal_response_fields`.
3. **Implementation:** Documented expected entry fields:
   `entry_id`, `payload_ref`, `approval_context`, `metadata`, `evidence_refs`,
   and `approval_indicator`.
4. **Verification:** Targeted docs contract test passed after doc update.
5. **Outcome/Learning:** Docs now clearly connect human-readable timeline output
   to traceable machine fields.

### Round 3 — Error Behavior Alignment

1. **Pattern Investigation:** Journal-specific error envelopes were not
   represented in testing instructions.
2. **Failing Tests:** Added
   `test_round3_api_testing_docs_capture_journal_error_behavior`.
3. **Implementation:** Added explicit expected outcomes for `404 RUN_NOT_FOUND`,
   `409 INCONSISTENT_RUN_STATE`, and `500 STORAGE_READ_ERROR`.
4. **Verification:** Targeted docs contract test passed after doc update.
5. **Outcome/Learning:** Fail-loud behavior is now testable from docs with
   concrete expected envelopes.

### Round 4 — Demo Readability + Traceability Narration

1. **Pattern Investigation:** `docs/DEMO_SCRIPT.md` remained a high-level draft
   and did not explicitly frame readability and traceability checkpoints.
2. **Failing Tests:** Added
   `test_round4_demo_script_calls_out_journal_readability_and_traceability`.
3. **Implementation:** Rewrote demo script with explicit sections for
   "journal readability demo" and "evidence traceability demo" using
   `/v1/runs/{run_id}/journal`.
4. **Verification:** Targeted docs contract test passed after doc update.
5. **Outcome/Learning:** Demo narrative now directly demonstrates the
   representation layer value proposition.

### Round 5 — Before/After Approval Transition Evidence

1. **Pattern Investigation:** Draft demo flow did not clearly compare journal
   state before vs after resolution.
2. **Failing Tests:** Added
   `test_round5_demo_script_includes_before_and_after_approval_journal_checks`.
3. **Implementation:** Added explicit "before approval resolution" and
   "after approval resolution" steps with `approval_indicator` interpretation.
4. **Verification:** `tests/test_journal_contract_docs.py` passed end-to-end.
5. **Outcome/Learning:** Demo now proves approval pause/resume behavior with
   projected timeline evidence.

### ✅ Final Audit Summary

- **Docs delivered:** `docs/API_TESTING.md` and `docs/DEMO_SCRIPT.md` now include
  practical journal endpoint runbook guidance.
- **Contract guardrails added:** `tests/test_journal_contract_docs.py` now
  enforces issue-35 doc acceptance criteria.
- **Verification completed:** `./.venv/bin/pytest -q tests/test_journal_contract_docs.py`
  passed (`11` tests).
- **Known verification gap:** Full suite run (`./.venv/bin/pytest -q`) was
  blocked in this environment due missing `httpx` and restricted network access
  preventing dependency install.
- **Issue #35 readiness decision:** **Ready** from a documentation scope
  perspective; all targeted doc acceptance checks are green.
## 🗓️ 2026-02-15: Issue #33 — Journal Projection Fixture Coverage (5-Round Big Slik Cycle)

### 🎯 Objective

Add focused unit coverage for journal projection behavior using realistic run
fixtures, including deterministic ordering guarantees, approval transition
rendering, and traceability/evidence linkage assertions.

### 🔁 The 5-Round Process (Human-readable)

### Round 1 — Baseline Fixture Mapping + Traceability

1. **Pattern Investigation:** Existing projector tests validated specific
   fields, but did not provide a dedicated fixture-driven event-type mapping
   sweep with per-entry payload linkage checks.
2. **Failing Tests:** Added
   `test_round1_projection_fixture_maps_event_types_and_traceability` in
   `tests/test_journal_projection.py` and initially left fixture helper missing
   to force a red test.
3. **Implementation:** Implemented `_happy_path_run_fixture` and `_stored_event`
   helpers to build realistic event streams.
4. **Verification:** Round 1 targeted test passed.
5. **Outcome/Learning:** Baseline fixture coverage now validates event-type
   mapping plus raw payload traceability for every entry.

### Round 2 — Out-of-Order Ingestion Determinism

1. **Pattern Investigation:** Issue acceptance required deterministic behavior
   when ingestion order does not match timestamp order.
2. **Failing Tests:** Added
   `test_round2_projection_fixture_is_deterministic_for_out_of_order_ingestion`
   with missing helper first to force failure.
3. **Implementation:** Added `_projected_entry_ids_for_out_of_order_ingestion`
   plus reusable `_event_payload` builder using
   `InMemoryAppendOnlyEventStore`.
4. **Verification:** Round 1-2 targeted tests passed.
5. **Outcome/Learning:** Projection ordering is now locked to deterministic
   sorted retrieval from append-only storage in realistic ingestion scenarios.

### Round 3 — Same-Timestamp Tie Determinism

1. **Pattern Investigation:** Deterministic ties at identical timestamps were
   not explicitly asserted in dedicated fixture tests.
2. **Failing Tests:** Added
   `test_round3_projection_fixture_is_deterministic_for_same_timestamp_ties`
   and intentionally failed on missing helper.
3. **Implementation:** Added `_projected_entry_ids_for_same_timestamp_ties`
   fixture helper.
4. **Verification:** Round 1-3 targeted tests passed.
5. **Outcome/Learning:** Tiebreak behavior is now explicitly covered as stable
   insertion-sequence ordering.

### Round 4 — Approval Pending/Resolved Rendering

1. **Pattern Investigation:** Approval rendering existed in prior tests, but
   issue #33 asked for fixture-based coverage focused on projection behavior.
2. **Failing Tests:** Added
   `test_round4_projection_fixture_renders_approval_pending_and_resolved_entries`
   with missing helper to force red.
3. **Implementation:** Added `_approval_flow_fixture_projection` and extended
   `_event_payload` to model approval metadata transitions.
4. **Verification:** Round 1-4 targeted tests passed.
5. **Outcome/Learning:** Fixture coverage now asserts both required and resolved
   approval rendering, including resolver identity and decision semantics.

### Round 5 — Edge Fixture Evidence + Raw Linkage Audit

1. **Pattern Investigation:** Acceptance required evidence/raw linkage
   assertions across every fixture entry, including edge paths.
2. **Failing Tests:** Added
   `test_round5_projection_edge_fixture_preserves_evidence_and_raw_linkage`
   with missing helper to force red.
3. **Implementation:** Added `_edge_path_projection_fixture` using out-of-order
   ingestion, pending approval, and rejected resolution flow.
4. **Verification:** `tests/test_journal_projection.py` passed end-to-end.
5. **Outcome/Learning:** Every edge fixture entry now asserts payload
   traceability and evidence references, with integrity warning and rejection
   semantics explicitly validated.

### ✅ Final Audit Summary

- **Issue-vs-implementation check:** Acceptance criteria satisfied in dedicated
  unit coverage:
  deterministic ordering (out-of-order + tie), approval-required/resolved
  rendering, and evidence/raw linkage assertions.
- **Code hygiene:** Added reusable fixture helpers to keep scenarios readable
  and avoid duplicated payload construction.
- **Validation completed:**
  - `./.venv/bin/pytest -q tests/test_journal_projection.py`
  - `./.venv/bin/pytest -q tests/test_journal_projection.py tests/test_journal_projection_service.py`
- **Environment limitation:** Full-suite run
  `./.venv/bin/pytest -q` is currently blocked in this sandbox because
  `httpx` is unavailable offline during dependency install.
- **Issue #33 readiness decision:** **Ready** for review; fixture-driven
  projection coverage added with deterministic and traceability guarantees.

## 🗓️ 2026-02-15: Issue #32 — Journal Endpoint Wiring (5-Round Big Slik Cycle)

### 🎯 Objective

Expose journal projection through `GET /v1/runs/{run_id}/journal` with
deterministic output and fail-loud error behavior consistent with existing API
patterns.

### 🔁 The 5-Round Process (Human-readable)

### Round 1 — Baseline Endpoint Wiring

1. **Pattern Investigation:** Confirmed journal projection service existed but
   controller route was missing.
2. **Failing Tests:** Added
   `test_round1_get_run_journal_returns_projection_for_known_run` in
   `tests/test_journal_api.py`.
3. **Implementation:** Wired `GET /v1/runs/{run_id}/journal` in
   `events_controller`, loading run events and returning
   `project_run_journal(...).to_dict()`.
4. **Verification:** Targeted journal API test passed, then full suite passed.
5. **Outcome/Learning:** Known-run journal projection became consumable over
   HTTP.

### Round 2 — Unknown Run Semantics

1. **Pattern Investigation:** Unknown runs returned `200` with empty projection,
   which violated the contract.
2. **Failing Tests:** Added
   `test_round2_get_run_journal_returns_not_found_for_unknown_run`.
3. **Implementation:** Raised `RunNotFoundError` when no run events exist.
4. **Verification:** Targeted test passed, then full suite passed.
5. **Outcome/Learning:** Endpoint now has explicit `404 RUN_NOT_FOUND`
   semantics.

### Round 3 — Storage Read Fail-Loud Wrapping

1. **Pattern Investigation:** Generic backend read faults bubbled as unhandled
   exceptions.
2. **Failing Tests:** Added
   `test_round3_get_run_journal_surfaces_storage_read_error` using a store that
   raises generic runtime errors.
3. **Implementation:** Added `StorageReadError` defensive wrapper in journal
   route, matching other endpoints.
4. **Verification:** Targeted test passed, then full suite passed.
5. **Outcome/Learning:** Read-path failures are now consistently mapped to
   `500 STORAGE_READ_ERROR`.

### Round 4 — Corrupt Timestamp Record Handling

1. **Pattern Investigation:** Malformed store records (`timestamp` not datetime)
   produced unstructured crashes.
2. **Failing Tests:** Added
   `test_round4_get_run_journal_surfaces_inconsistent_state_for_invalid_timestamp`.
3. **Implementation:** Added projector validation to raise
   `InconsistentRunStateError` with `INVALID_EVENT_TIMESTAMP`.
4. **Verification:** Targeted test passed, then full suite passed.
5. **Outcome/Learning:** Corrupt timestamp data now fails loudly as
   `409 INCONSISTENT_RUN_STATE`.

### Round 5 — Corrupt Payload Record Handling

1. **Pattern Investigation:** Non-object payload values still crashed during
   projection.
2. **Failing Tests:** Added
   `test_round5_get_run_journal_surfaces_inconsistent_state_for_invalid_payload`.
3. **Implementation:** Added payload-shape guard in projector to raise
   `InconsistentRunStateError` with `INVALID_EVENT_PAYLOAD`.
4. **Verification:** Targeted test passed, journal API suite passed, then full
   suite passed.
5. **Outcome/Learning:** Endpoint remains deterministic and transparent even for
   malformed storage records.

### ✅ Final Audit Summary

- **Controller delivery:** `GET /v1/runs/{run_id}/journal` added and wired to
  pure projection service.
- **Fail-loud coverage:** Explicit handling for unknown run, storage read
  failures, invalid timestamps, and invalid payloads.
- **Tests added:** Dedicated endpoint suite in `tests/test_journal_api.py`.
- **Final verification:** `111` tests passing (`./.venv/bin/pytest -q`).
- **Issue #32 readiness decision:** **Ready** for merge; acceptance criteria
  met with representation-only behavior and structured failure envelopes.

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
