#!/usr/bin/env bash
set -euo pipefail

# Local smoke checklist for GET /v1/runs/:runId/status.
# Usage:
#   bash tasks/smoke_status_curl.sh
# Optional env:
#   BASE_URL=http://127.0.0.1:8001
#   AUTO_START=0|1   (default: 1)

BASE_URL="${BASE_URL:-http://127.0.0.1:8001}"
AUTO_START="${AUTO_START:-1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_PYTHON="${REPO_ROOT}/.venv/bin/python"

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required"
  exit 1
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required"
  exit 1
fi

TMP_DIR="$(mktemp -d)"
API_PID=""

cleanup() {
  if [[ -n "${API_PID}" ]]; then
    kill "${API_PID}" >/dev/null 2>&1 || true
  fi
  rm -rf "${TMP_DIR}"
}
trap cleanup EXIT

wait_for_api() {
  for _ in {1..40}; do
    if curl -sS "${BASE_URL}/openapi.json" >/dev/null 2>&1; then
      return 0
    fi
    sleep 0.25
  done
  echo "API did not become ready at ${BASE_URL}"
  return 1
}

if [[ "${AUTO_START}" == "1" ]]; then
  if [[ ! -x "${VENV_PYTHON}" ]]; then
    echo "Python not found at ${VENV_PYTHON}."
    echo "Run this script from a repo with a configured .venv."
    exit 1
  fi
  if ! "${VENV_PYTHON}" -c "import uvicorn" >/dev/null 2>&1; then
    echo "AUTO_START=1 requires uvicorn in .venv."
    echo "Install uvicorn, or run with AUTO_START=0 against an already running API."
    exit 1
  fi
  PYTHONPATH="${REPO_ROOT}/src" "${VENV_PYTHON}" -m uvicorn nightledger_api.main:app \
    --host 127.0.0.1 --port 8001 >"${TMP_DIR}/api.log" 2>&1 &
  API_PID="$!"
  wait_for_api
fi

assert_eq() {
  local got="$1"
  local expected="$2"
  local label="$3"
  if [[ "${got}" != "${expected}" ]]; then
    echo "FAIL: ${label} (expected '${expected}', got '${got}')"
    exit 1
  fi
  echo "PASS: ${label}"
}

json_get() {
  local file="$1"
  local path="$2"
  python3 - "$file" "$path" <<'PY'
import json, sys
file_path, path = sys.argv[1], sys.argv[2]
with open(file_path, "r", encoding="utf-8") as f:
    data = json.load(f)
parts = path.split(".")
cur = data
for part in parts:
    if part == "null":
        break
    if isinstance(cur, list):
        cur = cur[int(part)]
    else:
        cur = cur.get(part)
if cur is None:
    print("null")
elif isinstance(cur, bool):
    print("true" if cur else "false")
else:
    print(cur)
PY
}

post_event() {
  local payload_file="$1"
  local out_file="$2"
  local code
  code="$(curl -sS -o "${out_file}" -w "%{http_code}" \
    -X POST "${BASE_URL}/v1/events" \
    -H "Content-Type: application/json" \
    --data-binary @"${payload_file}")"
  echo "${code}"
}

get_status() {
  local run_id="$1"
  local out_file="$2"
  local code
  code="$(curl -sS -o "${out_file}" -w "%{http_code}" \
    "${BASE_URL}/v1/runs/${run_id}/status")"
  echo "${code}"
}

TS="$(date +%s)"

echo "Running smoke checks against ${BASE_URL}"

# 1) Running
RUN_RUNNING="run_smoke_running_${TS}"
EVT_RUNNING="evt_smoke_running_${TS}"
cat >"${TMP_DIR}/running.json" <<JSON
{
  "id": "${EVT_RUNNING}",
  "run_id": "${RUN_RUNNING}",
  "timestamp": "2026-02-15T10:00:00Z",
  "type": "action",
  "actor": "agent",
  "title": "Action event",
  "details": "Normal execution",
  "confidence": 0.8,
  "risk_level": "low",
  "requires_approval": false,
  "approval": {
    "status": "not_required",
    "requested_by": null,
    "resolved_by": null,
    "resolved_at": null,
    "reason": null
  },
  "evidence": [{"kind": "log", "label": "Execution log", "ref": "log://smoke"}]
}
JSON
assert_eq "$(post_event "${TMP_DIR}/running.json" "${TMP_DIR}/post_running.out")" "201" "POST running event"
assert_eq "$(get_status "${RUN_RUNNING}" "${TMP_DIR}/status_running.out")" "200" "GET running status code"
assert_eq "$(json_get "${TMP_DIR}/status_running.out" "status")" "running" "running status"
assert_eq "$(json_get "${TMP_DIR}/status_running.out" "pending_approval")" "null" "running has no pending_approval"

# 2) Paused
RUN_PAUSED="run_smoke_paused_${TS}"
EVT_PAUSED="evt_smoke_paused_${TS}"
cat >"${TMP_DIR}/paused.json" <<JSON
{
  "id": "${EVT_PAUSED}",
  "run_id": "${RUN_PAUSED}",
  "timestamp": "2026-02-15T11:00:00Z",
  "type": "approval_requested",
  "actor": "agent",
  "title": "Approval required",
  "details": "Transfer exceeds threshold",
  "confidence": 0.8,
  "risk_level": "high",
  "requires_approval": true,
  "approval": {
    "status": "pending",
    "requested_by": "agent",
    "resolved_by": null,
    "resolved_at": null,
    "reason": "Transfer exceeds threshold"
  },
  "evidence": [{"kind": "log", "label": "Execution log", "ref": "log://smoke"}]
}
JSON
assert_eq "$(post_event "${TMP_DIR}/paused.json" "${TMP_DIR}/post_paused.out")" "201" "POST paused event"
assert_eq "$(get_status "${RUN_PAUSED}" "${TMP_DIR}/status_paused.out")" "200" "GET paused status code"
assert_eq "$(json_get "${TMP_DIR}/status_paused.out" "status")" "paused" "paused status"
assert_eq "$(json_get "${TMP_DIR}/status_paused.out" "pending_approval.event_id")" "${EVT_PAUSED}" "paused pending approval context"

# 3) Approved then running
RUN_APPROVED="run_smoke_approved_${TS}"
cat >"${TMP_DIR}/approved_req.json" <<JSON
{
  "id": "evt_smoke_approved_req_${TS}",
  "run_id": "${RUN_APPROVED}",
  "timestamp": "2026-02-15T12:00:00Z",
  "type": "approval_requested",
  "actor": "agent",
  "title": "Approval required",
  "details": "Need approval",
  "confidence": 0.8,
  "risk_level": "high",
  "requires_approval": true,
  "approval": {
    "status": "pending",
    "requested_by": "agent",
    "resolved_by": null,
    "resolved_at": null,
    "reason": "Need approval"
  },
  "evidence": [{"kind": "log", "label": "Execution log", "ref": "log://smoke"}]
}
JSON
cat >"${TMP_DIR}/approved_resolved.json" <<JSON
{
  "id": "evt_smoke_approved_resolved_${TS}",
  "run_id": "${RUN_APPROVED}",
  "timestamp": "2026-02-15T12:01:00Z",
  "type": "approval_resolved",
  "actor": "human",
  "title": "Approval resolved",
  "details": "Approved",
  "confidence": 1.0,
  "risk_level": "high",
  "requires_approval": true,
  "approval": {
    "status": "approved",
    "requested_by": "agent",
    "resolved_by": "human_reviewer",
    "resolved_at": "2026-02-15T12:01:00Z",
    "reason": "Looks good"
  },
  "evidence": [{"kind": "log", "label": "Execution log", "ref": "log://smoke"}]
}
JSON
cat >"${TMP_DIR}/approved_followup.json" <<JSON
{
  "id": "evt_smoke_approved_followup_${TS}",
  "run_id": "${RUN_APPROVED}",
  "timestamp": "2026-02-15T12:02:00Z",
  "type": "action",
  "actor": "agent",
  "title": "Continue execution",
  "details": "Resumed run after approval",
  "confidence": 0.8,
  "risk_level": "low",
  "requires_approval": false,
  "approval": {
    "status": "not_required",
    "requested_by": null,
    "resolved_by": null,
    "resolved_at": null,
    "reason": null
  },
  "evidence": [{"kind": "log", "label": "Execution log", "ref": "log://smoke"}]
}
JSON
assert_eq "$(post_event "${TMP_DIR}/approved_req.json" "${TMP_DIR}/post_approved_req.out")" "201" "POST approval request"
assert_eq "$(post_event "${TMP_DIR}/approved_resolved.json" "${TMP_DIR}/post_approved_resolved.out")" "201" "POST approval resolved"
assert_eq "$(get_status "${RUN_APPROVED}" "${TMP_DIR}/status_approved.out")" "200" "GET approved status code"
assert_eq "$(json_get "${TMP_DIR}/status_approved.out" "status")" "approved" "approved status"
assert_eq "$(post_event "${TMP_DIR}/approved_followup.json" "${TMP_DIR}/post_approved_followup.out")" "201" "POST follow-up action"
assert_eq "$(get_status "${RUN_APPROVED}" "${TMP_DIR}/status_running_after_approved.out")" "200" "GET running-after-approved status code"
assert_eq "$(json_get "${TMP_DIR}/status_running_after_approved.out" "status")" "running" "running after approved follow-up"

# 4) Rejected then invalid continuation
RUN_REJECTED="run_smoke_rejected_${TS}"
cat >"${TMP_DIR}/rejected_req.json" <<JSON
{
  "id": "evt_smoke_rejected_req_${TS}",
  "run_id": "${RUN_REJECTED}",
  "timestamp": "2026-02-15T13:00:00Z",
  "type": "approval_requested",
  "actor": "agent",
  "title": "Approval required",
  "details": "Need approval",
  "confidence": 0.8,
  "risk_level": "high",
  "requires_approval": true,
  "approval": {
    "status": "pending",
    "requested_by": "agent",
    "resolved_by": null,
    "resolved_at": null,
    "reason": "Need approval"
  },
  "evidence": [{"kind": "log", "label": "Execution log", "ref": "log://smoke"}]
}
JSON
cat >"${TMP_DIR}/rejected_resolved.json" <<JSON
{
  "id": "evt_smoke_rejected_resolved_${TS}",
  "run_id": "${RUN_REJECTED}",
  "timestamp": "2026-02-15T13:01:00Z",
  "type": "approval_resolved",
  "actor": "human",
  "title": "Approval rejected",
  "details": "Rejected",
  "confidence": 1.0,
  "risk_level": "high",
  "requires_approval": true,
  "approval": {
    "status": "rejected",
    "requested_by": "agent",
    "resolved_by": "human_reviewer",
    "resolved_at": "2026-02-15T13:01:00Z",
    "reason": "Policy violation"
  },
  "evidence": [{"kind": "log", "label": "Execution log", "ref": "log://smoke"}]
}
JSON
cat >"${TMP_DIR}/rejected_followup.json" <<JSON
{
  "id": "evt_smoke_rejected_followup_${TS}",
  "run_id": "${RUN_REJECTED}",
  "timestamp": "2026-02-15T13:02:00Z",
  "type": "action",
  "actor": "agent",
  "title": "Invalid continuation",
  "details": "Continuation after rejection",
  "confidence": 0.8,
  "risk_level": "low",
  "requires_approval": false,
  "approval": {
    "status": "not_required",
    "requested_by": null,
    "resolved_by": null,
    "resolved_at": null,
    "reason": null
  },
  "evidence": [{"kind": "log", "label": "Execution log", "ref": "log://smoke"}]
}
JSON
assert_eq "$(post_event "${TMP_DIR}/rejected_req.json" "${TMP_DIR}/post_rejected_req.out")" "201" "POST rejected request"
assert_eq "$(post_event "${TMP_DIR}/rejected_resolved.json" "${TMP_DIR}/post_rejected_resolved.out")" "201" "POST rejected resolution"
assert_eq "$(get_status "${RUN_REJECTED}" "${TMP_DIR}/status_rejected.out")" "200" "GET rejected status code"
assert_eq "$(json_get "${TMP_DIR}/status_rejected.out" "status")" "rejected" "rejected status"
assert_eq "$(post_event "${TMP_DIR}/rejected_followup.json" "${TMP_DIR}/post_rejected_followup.out")" "201" "POST rejected follow-up event"
assert_eq "$(get_status "${RUN_REJECTED}" "${TMP_DIR}/status_rejected_conflict.out")" "409" "GET rejected continuation conflict code"
assert_eq "$(json_get "${TMP_DIR}/status_rejected_conflict.out" "error.details.0.code")" "REJECTED_STATE_CONFLICT" "rejected continuation conflict code detail"

# 5) Unknown run
assert_eq "$(get_status "run_smoke_missing_${TS}" "${TMP_DIR}/status_missing.out")" "404" "GET unknown run code"
assert_eq "$(json_get "${TMP_DIR}/status_missing.out" "error.code")" "RUN_NOT_FOUND" "unknown run error code"

# 6) approval_resolved without pending
RUN_NO_PENDING="run_smoke_no_pending_${TS}"
cat >"${TMP_DIR}/no_pending.json" <<JSON
{
  "id": "evt_smoke_no_pending_${TS}",
  "run_id": "${RUN_NO_PENDING}",
  "timestamp": "2026-02-15T14:00:00Z",
  "type": "approval_resolved",
  "actor": "human",
  "title": "Invalid resolution",
  "details": "Resolved without pending",
  "confidence": 1.0,
  "risk_level": "high",
  "requires_approval": true,
  "approval": {
    "status": "approved",
    "requested_by": "agent",
    "resolved_by": "human_reviewer",
    "resolved_at": "2026-02-15T14:00:00Z",
    "reason": "n/a"
  },
  "evidence": [{"kind": "log", "label": "Execution log", "ref": "log://smoke"}]
}
JSON
assert_eq "$(post_event "${TMP_DIR}/no_pending.json" "${TMP_DIR}/post_no_pending.out")" "201" "POST no-pending resolution event"
assert_eq "$(get_status "${RUN_NO_PENDING}" "${TMP_DIR}/status_no_pending.out")" "409" "GET no-pending conflict code"
assert_eq "$(json_get "${TMP_DIR}/status_no_pending.out" "error.details.0.code")" "NO_PENDING_APPROVAL" "no-pending conflict detail"

echo "All smoke checks passed."
