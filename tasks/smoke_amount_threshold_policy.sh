#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8001}"
AUTO_START="${AUTO_START:-1}"
POLICY_THRESHOLD_EUR="${POLICY_THRESHOLD_EUR:-100}"
EXECUTION_TOKEN_SECRET="${NIGHTLEDGER_EXECUTION_TOKEN_SECRET:-smoke-policy-secret-key-material-32b}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_PYTHON="${REPO_ROOT}/.venv/bin/python"
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
  echo "API did not become ready at ${BASE_URL}" >&2
  return 1
}

require_tools() {
  if ! command -v curl >/dev/null 2>&1; then
    echo "curl is required" >&2
    exit 1
  fi
  if ! command -v python3 >/dev/null 2>&1; then
    echo "python3 is required" >&2
    exit 1
  fi
}

post_json() {
  local output_file="$1"
  local payload="$2"
  curl -sS -o "${output_file}" -w "%{http_code}" \
    -X POST "${BASE_URL}/v1/mcp/authorize_action" \
    -H "Content-Type: application/json" \
    -d "${payload}"
}

assert_success_case() {
  local file_path="$1"
  local expected_state="$2"
  local expected_reason="$3"
  local label="$4"
  python3 - "${file_path}" "${expected_state}" "${expected_reason}" "${label}" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
expected_state = sys.argv[2]
expected_reason = sys.argv[3]
label = sys.argv[4]
body = json.loads(path.read_text())

if body.get("state") != expected_state:
    raise SystemExit(f"{label}: expected state={expected_state}, got {body.get('state')}")
if body.get("reason_code") != expected_reason:
    raise SystemExit(
        f"{label}: expected reason_code={expected_reason}, got {body.get('reason_code')}"
    )
if not str(body.get("decision_id", "")).startswith("dec_"):
    raise SystemExit(f"{label}: decision_id missing or malformed")
print(f"{label}: PASS state={body['state']} reason_code={body['reason_code']}")
PY
}

assert_validation_case() {
  local file_path="$1"
  local expected_code="$2"
  local expected_path="$3"
  local label="$4"
  python3 - "${file_path}" "${expected_code}" "${expected_path}" "${label}" <<'PY'
import json
import sys
from pathlib import Path

path = Path(sys.argv[1])
expected_code = sys.argv[2]
expected_path = sys.argv[3]
label = sys.argv[4]
body = json.loads(path.read_text())

error = body.get("error", {})
if error.get("code") != "REQUEST_VALIDATION_ERROR":
    raise SystemExit(f"{label}: expected REQUEST_VALIDATION_ERROR envelope")

details = error.get("details", [])
codes = {detail.get("path"): detail.get("code") for detail in details}
if codes.get(expected_path) != expected_code:
    raise SystemExit(
        f"{label}: expected {expected_path}={expected_code}, got {codes.get(expected_path)}"
    )
print(f"{label}: PASS path={expected_path} code={expected_code}")
PY
}

require_tools

if [[ "${AUTO_START}" == "1" ]]; then
  if [[ ! -x "${VENV_PYTHON}" ]]; then
    echo "Python not found at ${VENV_PYTHON}" >&2
    exit 1
  fi
  if ! "${VENV_PYTHON}" -c "import uvicorn" >/dev/null 2>&1; then
    echo "AUTO_START=1 requires uvicorn in .venv." >&2
    exit 1
  fi
  NIGHTLEDGER_PURCHASE_APPROVAL_THRESHOLD_EUR="${POLICY_THRESHOLD_EUR}" \
    NIGHTLEDGER_EXECUTION_TOKEN_SECRET="${EXECUTION_TOKEN_SECRET}" \
    PYTHONPATH="${REPO_ROOT}/src" "${VENV_PYTHON}" -m uvicorn nightledger_api.main:app \
      --host 127.0.0.1 --port 8001 >"${TMP_DIR}/api.log" 2>&1 &
  API_PID="$!"
  wait_for_api
fi

ABOVE_THRESHOLD="$(python3 - "${POLICY_THRESHOLD_EUR}" <<'PY'
import sys
print(float(sys.argv[1]) + 1)
PY
)"

HTTP_CODE_1="$(post_json "${TMP_DIR}/at_threshold.json" \
  "{\"intent\":{\"action\":\"purchase.create\"},\"context\":{\"request_id\":\"req_threshold\",\"amount\":${POLICY_THRESHOLD_EUR},\"currency\":\"EUR\",\"transport_decision_hint\":\"deny\"}}")"
if [[ "${HTTP_CODE_1}" != "200" ]]; then
  echo "at-threshold case failed with HTTP ${HTTP_CODE_1}" >&2
  cat "${TMP_DIR}/at_threshold.json" >&2
  exit 1
fi
assert_success_case "${TMP_DIR}/at_threshold.json" "allow" "POLICY_ALLOW_WITHIN_THRESHOLD" "at-threshold"

HTTP_CODE_2="$(post_json "${TMP_DIR}/above_threshold.json" \
  "{\"intent\":{\"action\":\"purchase.create\"},\"context\":{\"request_id\":\"req_above\",\"amount\":${ABOVE_THRESHOLD},\"currency\":\"EUR\",\"transport_decision_hint\":\"allow\"}}")"
if [[ "${HTTP_CODE_2}" != "200" ]]; then
  echo "above-threshold case failed with HTTP ${HTTP_CODE_2}" >&2
  cat "${TMP_DIR}/above_threshold.json" >&2
  exit 1
fi
assert_success_case "${TMP_DIR}/above_threshold.json" "requires_approval" "AMOUNT_ABOVE_THRESHOLD" "above-threshold"

HTTP_CODE_3="$(post_json "${TMP_DIR}/missing_amount.json" \
  "{\"intent\":{\"action\":\"purchase.create\"},\"context\":{\"request_id\":\"req_missing_amount\",\"currency\":\"EUR\"}}")"
if [[ "${HTTP_CODE_3}" != "422" ]]; then
  echo "missing-amount case failed with HTTP ${HTTP_CODE_3}" >&2
  cat "${TMP_DIR}/missing_amount.json" >&2
  exit 1
fi
assert_validation_case "${TMP_DIR}/missing_amount.json" "MISSING_AMOUNT" "context.amount" "missing-amount"

HTTP_CODE_4="$(post_json "${TMP_DIR}/unsupported_currency.json" \
  "{\"intent\":{\"action\":\"purchase.create\"},\"context\":{\"request_id\":\"req_bad_currency\",\"amount\":10,\"currency\":\"USD\"}}")"
if [[ "${HTTP_CODE_4}" != "422" ]]; then
  echo "unsupported-currency case failed with HTTP ${HTTP_CODE_4}" >&2
  cat "${TMP_DIR}/unsupported_currency.json" >&2
  exit 1
fi
assert_validation_case "${TMP_DIR}/unsupported_currency.json" "UNSUPPORTED_CURRENCY" "context.currency" "unsupported-currency"

echo "policy-threshold smoke: PASS (threshold=${POLICY_THRESHOLD_EUR} EUR)"
