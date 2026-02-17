#!/usr/bin/env bash
set -euo pipefail

# NightLedger business-rule smoke checks (human-readable).
#
# Purpose:
#   Validate governance hardening behaviors from Issue #12 at API boundary.
#   This script focuses on "fail loud, fail structured" behavior for illegal
#   approval and terminal-state transitions.
#
# Usage:
#   bash tasks/smoke_business_rule_validation.sh
#
# Optional env:
#   BASE_URL=http://127.0.0.1:8001
#   AUTO_START=0|1      (default: 0; set 1 to auto-start API from .venv)
#   VERBOSE=0|1         (default: 1; set 0 for concise mode)
#
# Exit codes:
#   0 = all checks passed
#   1 = at least one check failed

BASE_URL="${BASE_URL:-http://127.0.0.1:8001}"
AUTO_START="${AUTO_START:-0}"
VERBOSE="${VERBOSE:-1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_PYTHON="${REPO_ROOT}/.venv/bin/python"
TMP_DIR="$(mktemp -d)"
API_PID=""
PASS_COUNT=0
FAIL_COUNT=0

cleanup() {
  if [[ -n "${API_PID}" ]]; then
    kill "${API_PID}" >/dev/null 2>&1 || true
  fi
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

require_cmd() {
  local cmd="$1"
  if ! command -v "${cmd}" >/dev/null 2>&1; then
    echo "Missing required command: ${cmd}" >&2
    exit 1
  fi
}

wait_for_api() {
  for _ in {1..60}; do
    if curl -sS "${BASE_URL}/openapi.json" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.25
  done
  echo "API did not become ready at ${BASE_URL}" >&2
  return 1
}

post_json() {
  local endpoint="$1"
  local body="$2"
  local out_file="$3"
  curl -sS -o "${out_file}" -w "%{http_code}" \
    -X POST "${BASE_URL}${endpoint}" \
    -H "Content-Type: application/json" \
    --data-binary "${body}"
}

json_get() {
  local file="$1"
  local path="$2"
  python3 - "$file" "$path" <<'PY'
import json
import sys

file_path = sys.argv[1]
path = sys.argv[2]

with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)

cur = data
for token in path.split("."):
    if token == "":
        continue
    if isinstance(cur, list):
        cur = cur[int(token)]
    else:
        cur = cur.get(token)

if cur is None:
    print("null")
elif isinstance(cur, bool):
    print("true" if cur else "false")
else:
    print(str(cur))
PY
}

note() {
  local msg="$1"
  if [[ "${VERBOSE}" == "1" ]]; then
    echo "${msg}"
  fi
}

print_title() {
  local title="$1"
  local explanation="$2"
  echo
  echo "--------------------------------------------------------------------------------"
  echo "${title}"
  echo "${explanation}"
}

record_pass() {
  local label="$1"
  PASS_COUNT=$((PASS_COUNT + 1))
  echo "PASS: ${label}"
}

record_fail() {
  local label="$1"
  local body_file="$2"
  FAIL_COUNT=$((FAIL_COUNT + 1))
  echo "FAIL: ${label}"
  echo "Response body:"
  if command -v python3 >/dev/null 2>&1; then
    python3 -m json.tool <"${body_file}" || cat "${body_file}"
  else
    cat "${body_file}"
  fi
}

assert_http_code() {
  local got="$1"
  local expected="$2"
  local label="$3"
  local body_file="$4"
  if [[ "${got}" != "${expected}" ]]; then
    record_fail "${label} (expected HTTP ${expected}, got ${got})" "${body_file}"
    return 1
  fi
  record_pass "${label}"
  return 0
}

assert_json_eq() {
  local file="$1"
  local path="$2"
  local expected="$3"
  local label="$4"
  local got
  got="$(json_get "${file}" "${path}")"
  if [[ "${got}" != "${expected}" ]]; then
    FAIL_COUNT=$((FAIL_COUNT + 1))
    echo "FAIL: ${label}"
    echo "  path: ${path}"
    echo "  expected: ${expected}"
    echo "  got: ${got}"
    echo "Response body:"
    if command -v python3 >/dev/null 2>&1; then
      python3 -m json.tool <"${file}" || cat "${file}"
    else
      cat "${file}"
    fi
    return 1
  fi
  PASS_COUNT=$((PASS_COUNT + 1))
  echo "PASS: ${label}"
  return 0
}

run_case() {
  local case_id="$1"
  local title="$2"
  local explanation="$3"
  local endpoint="$4"
  local payload="$5"
  local expected_http="$6"
  local expected_code="$7"
  local expected_rule="$8"
  local expected_detail_code="$9"

  local out_file="${TMP_DIR}/${case_id}.json"
  local http

  print_title "${title}" "${explanation}"
  note "Request endpoint: ${endpoint}"
  http="$(post_json "${endpoint}" "${payload}" "${out_file}")"
  assert_http_code "${http}" "${expected_http}" "${case_id}: status code" "${out_file}" || return 1

  if [[ "${expected_http}" == "201" ]]; then
    assert_json_eq "${out_file}" "status" "accepted" "${case_id}: accepted envelope"
    return 0
  fi

  assert_json_eq "${out_file}" "error.code" "${expected_code}" "${case_id}: error envelope code"
  assert_json_eq "${out_file}" "error.details.0.code" "${expected_detail_code}" "${case_id}: detail code"

  if [[ "${expected_rule}" != "-" ]]; then
    assert_json_eq "${out_file}" "error.details.0.rule_id" "${expected_rule}" "${case_id}: rule id"
  fi
}

main() {
  require_cmd curl
  require_cmd python3

  if [[ "${AUTO_START}" == "1" ]]; then
    if [[ ! -x "${VENV_PYTHON}" ]]; then
      echo "Python not found at ${VENV_PYTHON}" >&2
      exit 1
    fi
    if ! "${VENV_PYTHON}" -c "import uvicorn" >/dev/null 2>&1; then
      echo "AUTO_START=1 requires uvicorn in .venv." >&2
      exit 1
    fi
    PYTHONPATH="${REPO_ROOT}/src" "${VENV_PYTHON}" -m uvicorn nightledger_api.main:app \
      --host 127.0.0.1 --port 8001 >"${TMP_DIR}/api.log" 2>&1 &
    API_PID="$!"
    wait_for_api
  else
    wait_for_api
  fi

  local ts
  ts="$(date +%s)"

  cat <<'TXT'
NightLedger Business Rule Validation Smoke Suite

This script tests the API-level governance guards that protect run integrity:
1) Illegal approval state combinations are rejected at ingest time.
2) Every rejection is structured and includes rule references.
3) Terminal runs cannot be mutated by later events.

Interpretation:
- PASS means the guard is active and returning expected machine-readable details.
- FAIL means either behavior drifted or the API contract changed.
TXT

  local run1="run_br_pending_${ts}"
  run_case \
    "case_1_rule_gate_001_status" \
    "Case 1: approval_requested must use pending status (RULE-GATE-001)" \
    "Why it matters: a gate request must be explicitly pending; otherwise UI/ops see a gate that is not actually open." \
    "/v1/events" \
    "{\"id\":\"evt_${ts}_1\",\"run_id\":\"${run1}\",\"timestamp\":\"2026-02-17T20:00:00Z\",\"type\":\"approval_requested\",\"actor\":\"agent\",\"title\":\"Approval needed\",\"details\":\"Check refund\",\"confidence\":0.8,\"risk_level\":\"high\",\"requires_approval\":true,\"approval\":{\"status\":\"not_required\",\"requested_by\":\"agent\",\"resolved_by\":null,\"resolved_at\":null,\"reason\":null},\"evidence\":[]}" \
    "409" \
    "BUSINESS_RULE_VIOLATION" \
    "RULE-GATE-001" \
    "INVALID_APPROVAL_TRANSITION"

  local run2="run_br_pending_flag_${ts}"
  run_case \
    "case_2_rule_gate_001_flag" \
    "Case 2: approval_requested must set requires_approval=true (RULE-GATE-001)" \
    "Why it matters: approval gates must be represented consistently in both boolean and status fields to prevent silent ambiguity." \
    "/v1/events" \
    "{\"id\":\"evt_${ts}_2\",\"run_id\":\"${run2}\",\"timestamp\":\"2026-02-17T20:01:00Z\",\"type\":\"approval_requested\",\"actor\":\"agent\",\"title\":\"Approval needed\",\"details\":\"Check delete\",\"confidence\":0.8,\"risk_level\":\"high\",\"requires_approval\":false,\"approval\":{\"status\":\"pending\",\"requested_by\":\"agent\",\"resolved_by\":null,\"resolved_at\":null,\"reason\":null},\"evidence\":[]}" \
    "409" \
    "BUSINESS_RULE_VIOLATION" \
    "RULE-GATE-001" \
    "INVALID_APPROVAL_TRANSITION"

  local run3="run_br_no_pending_${ts}"
  run_case \
    "case_3_rule_gate_002" \
    "Case 3: approval_resolved requires an active pending gate (RULE-GATE-002)" \
    "Why it matters: approvals cannot be resolved out-of-thin-air; resolution must reference an actual paused state in the run timeline." \
    "/v1/events" \
    "{\"id\":\"evt_${ts}_3\",\"run_id\":\"${run3}\",\"timestamp\":\"2026-02-17T20:02:00Z\",\"type\":\"approval_resolved\",\"actor\":\"human\",\"title\":\"Resolved\",\"details\":\"approved\",\"confidence\":0.8,\"risk_level\":\"high\",\"requires_approval\":true,\"approval\":{\"status\":\"approved\",\"requested_by\":\"agent\",\"resolved_by\":\"human_1\",\"resolved_at\":\"2026-02-17T20:02:00Z\",\"reason\":\"ok\"},\"evidence\":[]}" \
    "409" \
    "BUSINESS_RULE_VIOLATION" \
    "RULE-GATE-002" \
    "NO_PENDING_APPROVAL"

  local run4="run_br_missing_approver_${ts}"
  local out_a="${TMP_DIR}/case_4_setup.json"
  local http_a
  print_title \
    "Case 4: resolved approval requires approver identity (RULE-GATE-007)" \
    "Why it matters: every human decision must be attributable; missing resolver identity breaks accountability."
  http_a="$(post_json "/v1/events" \
    "{\"id\":\"evt_${ts}_4a\",\"run_id\":\"${run4}\",\"timestamp\":\"2026-02-17T20:03:00Z\",\"type\":\"approval_requested\",\"actor\":\"agent\",\"title\":\"Approval needed\",\"details\":\"Check refund\",\"confidence\":0.8,\"risk_level\":\"high\",\"requires_approval\":true,\"approval\":{\"status\":\"pending\",\"requested_by\":\"agent\",\"resolved_by\":null,\"resolved_at\":null,\"reason\":null},\"evidence\":[]}" \
    "${out_a}")"
  assert_http_code "${http_a}" "201" "case_4 setup pending event" "${out_a}"
  run_case \
    "case_4_rule_gate_007" \
    "Case 4b: missing resolved_by should be rejected" \
    "Expected result: 409 BUSINESS_RULE_VIOLATION with MISSING_APPROVER_ID and RULE-GATE-007." \
    "/v1/events" \
    "{\"id\":\"evt_${ts}_4b\",\"run_id\":\"${run4}\",\"timestamp\":\"2026-02-17T20:03:10Z\",\"type\":\"approval_resolved\",\"actor\":\"human\",\"title\":\"Resolved\",\"details\":\"approved\",\"confidence\":0.8,\"risk_level\":\"high\",\"requires_approval\":true,\"approval\":{\"status\":\"approved\",\"requested_by\":\"agent\",\"resolved_by\":null,\"resolved_at\":\"2026-02-17T20:03:10Z\",\"reason\":\"ok\"},\"evidence\":[]}" \
    "409" \
    "BUSINESS_RULE_VIOLATION" \
    "RULE-GATE-007" \
    "MISSING_APPROVER_ID"

  local run5="run_br_missing_timestamp_${ts}"
  local out_b="${TMP_DIR}/case_5_setup.json"
  local http_b
  print_title \
    "Case 5: resolved approval requires resolution timestamp (RULE-GATE-008)" \
    "Why it matters: approval chronology must be auditable; missing resolved_at removes temporal traceability."
  http_b="$(post_json "/v1/events" \
    "{\"id\":\"evt_${ts}_5a\",\"run_id\":\"${run5}\",\"timestamp\":\"2026-02-17T20:04:00Z\",\"type\":\"approval_requested\",\"actor\":\"agent\",\"title\":\"Approval needed\",\"details\":\"Check refund\",\"confidence\":0.8,\"risk_level\":\"high\",\"requires_approval\":true,\"approval\":{\"status\":\"pending\",\"requested_by\":\"agent\",\"resolved_by\":null,\"resolved_at\":null,\"reason\":null},\"evidence\":[]}" \
    "${out_b}")"
  assert_http_code "${http_b}" "201" "case_5 setup pending event" "${out_b}"
  run_case \
    "case_5_rule_gate_008" \
    "Case 5b: missing resolved_at should be rejected" \
    "Expected result: 409 BUSINESS_RULE_VIOLATION with MISSING_APPROVAL_TIMESTAMP and RULE-GATE-008." \
    "/v1/events" \
    "{\"id\":\"evt_${ts}_5b\",\"run_id\":\"${run5}\",\"timestamp\":\"2026-02-17T20:04:10Z\",\"type\":\"approval_resolved\",\"actor\":\"human\",\"title\":\"Resolved\",\"details\":\"approved\",\"confidence\":0.8,\"risk_level\":\"high\",\"requires_approval\":true,\"approval\":{\"status\":\"approved\",\"requested_by\":\"agent\",\"resolved_by\":\"human_1\",\"resolved_at\":null,\"reason\":\"ok\"},\"evidence\":[]}" \
    "409" \
    "BUSINESS_RULE_VIOLATION" \
    "RULE-GATE-008" \
    "MISSING_APPROVAL_TIMESTAMP"

  local run6="run_br_terminal_${ts}"
  local out_c="${TMP_DIR}/case_6_setup.json"
  local http_c
  print_title \
    "Case 6: terminal runs reject later mutating events (RULE-GATE-005)" \
    "Why it matters: after terminal completion, additional actions would silently mutate a finished run."
  http_c="$(post_json "/v1/events" \
    "{\"id\":\"evt_${ts}_6a\",\"run_id\":\"${run6}\",\"timestamp\":\"2026-02-17T20:05:00Z\",\"type\":\"summary\",\"actor\":\"agent\",\"title\":\"Completed\",\"details\":\"run complete\",\"confidence\":0.9,\"risk_level\":\"low\",\"requires_approval\":false,\"approval\":{\"status\":\"not_required\",\"requested_by\":null,\"resolved_by\":null,\"resolved_at\":null,\"reason\":null},\"evidence\":[]}" \
    "${out_c}")"
  assert_http_code "${http_c}" "201" "case_6 setup terminal summary" "${out_c}"
  run_case \
    "case_6_rule_gate_005" \
    "Case 6b: post-terminal action should be rejected" \
    "Expected result: 409 BUSINESS_RULE_VIOLATION with TERMINAL_STATE_CONFLICT and RULE-GATE-005." \
    "/v1/events" \
    "{\"id\":\"evt_${ts}_6b\",\"run_id\":\"${run6}\",\"timestamp\":\"2026-02-17T20:05:01Z\",\"type\":\"action\",\"actor\":\"agent\",\"title\":\"Late action\",\"details\":\"should not append\",\"confidence\":0.7,\"risk_level\":\"low\",\"requires_approval\":false,\"approval\":{\"status\":\"not_required\",\"requested_by\":null,\"resolved_by\":null,\"resolved_at\":null,\"reason\":null},\"evidence\":[]}" \
    "409" \
    "BUSINESS_RULE_VIOLATION" \
    "RULE-GATE-005" \
    "TERMINAL_STATE_CONFLICT"

  echo
  echo "================================================================================"
  echo "Smoke suite complete."
  echo "Passed checks: ${PASS_COUNT}"
  echo "Failed checks: ${FAIL_COUNT}"

  if [[ "${FAIL_COUNT}" -gt 0 ]]; then
    echo "Result: FAIL"
    exit 1
  fi
  echo "Result: PASS"
}

main "$@"
