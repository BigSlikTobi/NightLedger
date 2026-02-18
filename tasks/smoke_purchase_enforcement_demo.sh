#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8001}"
AUTO_START="${AUTO_START:-1}"
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

assert_json() {
  local file_path="$1"
  local script="$2"
  python3 - "${file_path}" "${script}" <<'PY'
import json
import sys
from pathlib import Path

body = json.loads(Path(sys.argv[1]).read_text())
exec(sys.argv[2], {"body": body})
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
  NIGHTLEDGER_EXECUTION_TOKEN_SECRET="issue49-demo-secret-key-material-32!!" \
    PYTHONPATH="${REPO_ROOT}/src" "${VENV_PYTHON}" -m uvicorn nightledger_api.main:app \
      --host 127.0.0.1 --port 8001 >"${TMP_DIR}/api.log" 2>&1 &
  API_PID="$!"
  wait_for_api
fi

HTTP_CODE_1="$(curl -sS -o "${TMP_DIR}/authorize.json" -w "%{http_code}" \
  -X POST "${BASE_URL}/v1/mcp/authorize_action" \
  -H "Content-Type: application/json" \
  -d '{"intent":{"action":"purchase.create"},"context":{"request_id":"req_issue49_demo","amount":500,"currency":"EUR","merchant":"ACME GmbH"}}')"
if [[ "${HTTP_CODE_1}" != "200" ]]; then
  echo "authorize_action failed with HTTP ${HTTP_CODE_1}" >&2
  cat "${TMP_DIR}/authorize.json" >&2
  exit 1
fi

assert_json "${TMP_DIR}/authorize.json" '
if body.get("state") != "requires_approval":
    raise SystemExit(f"expected requires_approval, got {body.get('"'"'state'"'"')}")
if body.get("reason_code") != "AMOUNT_ABOVE_THRESHOLD":
    raise SystemExit(f"expected AMOUNT_ABOVE_THRESHOLD, got {body.get('"'"'reason_code'"'"')}")
if not str(body.get("decision_id", "")).startswith("dec_"):
    raise SystemExit("decision_id missing or malformed")
'
DECISION_ID="$(python3 - "${TMP_DIR}/authorize.json" <<'PY'
import json
import sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text())["decision_id"])
PY
)"
echo "STEP 1 PASS: authorize_action returned requires_approval for 500 EUR"

HTTP_CODE_2="$(curl -sS -o "${TMP_DIR}/blocked.json" -w "%{http_code}" \
  -X POST "${BASE_URL}/v1/executors/purchase.create" \
  -H "Content-Type: application/json" \
  -d '{"amount":500,"currency":"EUR","merchant":"ACME GmbH"}')"
if [[ "${HTTP_CODE_2}" != "403" ]]; then
  echo "executor without token expected 403, got ${HTTP_CODE_2}" >&2
  cat "${TMP_DIR}/blocked.json" >&2
  exit 1
fi
assert_json "${TMP_DIR}/blocked.json" '
if body.get("error", {}).get("code") != "EXECUTION_TOKEN_MISSING":
    raise SystemExit("expected EXECUTION_TOKEN_MISSING")
'
echo "STEP 2 PASS: purchase executor blocked without token"

HTTP_CODE_3A="$(curl -sS -o "${TMP_DIR}/approval_request.json" -w "%{http_code}" \
  -X POST "${BASE_URL}/v1/approvals/requests" \
  -H "Content-Type: application/json" \
  -d "{\"decision_id\":\"${DECISION_ID}\",\"run_id\":\"run_issue49_demo\",\"requested_by\":\"agent\",\"title\":\"Approval required\",\"details\":\"Purchase amount exceeds threshold\",\"risk_level\":\"high\",\"reason\":\"Above threshold\"}")"
if [[ "${HTTP_CODE_3A}" != "200" ]]; then
  echo "approval request registration failed with HTTP ${HTTP_CODE_3A}" >&2
  cat "${TMP_DIR}/approval_request.json" >&2
  exit 1
fi

HTTP_CODE_3B="$(curl -sS -o "${TMP_DIR}/mint_pending.json" -w "%{http_code}" \
  -X POST "${BASE_URL}/v1/approvals/decisions/${DECISION_ID}/execution-token" \
  -H "Content-Type: application/json" \
  -d '{"amount":500,"currency":"EUR","merchant":"ACME GmbH"}')"
if [[ "${HTTP_CODE_3B}" != "409" ]]; then
  echo "pending decision mint expected 409, got ${HTTP_CODE_3B}" >&2
  cat "${TMP_DIR}/mint_pending.json" >&2
  exit 1
fi
assert_json "${TMP_DIR}/mint_pending.json" '
if body.get("error", {}).get("code") != "EXECUTION_DECISION_NOT_APPROVED":
    raise SystemExit("expected EXECUTION_DECISION_NOT_APPROVED")
'
echo "STEP 3 PASS: execution token mint blocked before approval"

HTTP_CODE_4="$(curl -sS -o "${TMP_DIR}/approve.json" -w "%{http_code}" \
  -X POST "${BASE_URL}/v1/approvals/decisions/${DECISION_ID}" \
  -H "Content-Type: application/json" \
  -d '{"decision":"approved","approver_id":"human_reviewer"}')"
if [[ "${HTTP_CODE_4}" != "200" ]]; then
  echo "approval resolution failed with HTTP ${HTTP_CODE_4}" >&2
  cat "${TMP_DIR}/approve.json" >&2
  exit 1
fi
assert_json "${TMP_DIR}/approve.json" '
if body.get("status") != "resolved":
    raise SystemExit("expected resolved status")
if body.get("decision") != "approved":
    raise SystemExit("expected approved decision")
'
echo "STEP 4 PASS: decision approved by human reviewer"

HTTP_CODE_5="$(curl -sS -o "${TMP_DIR}/mint_approved.json" -w "%{http_code}" \
  -X POST "${BASE_URL}/v1/approvals/decisions/${DECISION_ID}/execution-token" \
  -H "Content-Type: application/json" \
  -d '{"amount":500,"currency":"EUR","merchant":"ACME GmbH"}')"
if [[ "${HTTP_CODE_5}" != "200" ]]; then
  echo "execution token mint after approval failed with HTTP ${HTTP_CODE_5}" >&2
  cat "${TMP_DIR}/mint_approved.json" >&2
  exit 1
fi
assert_json "${TMP_DIR}/mint_approved.json" '
if not body.get("execution_token"):
    raise SystemExit("execution_token missing")
if body.get("action") != "purchase.create":
    raise SystemExit("expected purchase.create action")
'
EXEC_TOKEN="$(python3 - "${TMP_DIR}/mint_approved.json" <<'PY'
import json
import sys
from pathlib import Path
print(json.loads(Path(sys.argv[1]).read_text())["execution_token"])
PY
)"
echo "STEP 5 PASS: execution token minted after approval"

HTTP_CODE_6="$(curl -sS -o "${TMP_DIR}/execute.json" -w "%{http_code}" \
  -X POST "${BASE_URL}/v1/executors/purchase.create" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer ${EXEC_TOKEN}" \
  -d '{"amount":500,"currency":"EUR","merchant":"ACME GmbH"}')"
if [[ "${HTTP_CODE_6}" != "200" ]]; then
  echo "purchase executor with valid token failed with HTTP ${HTTP_CODE_6}" >&2
  cat "${TMP_DIR}/execute.json" >&2
  exit 1
fi
assert_json "${TMP_DIR}/execute.json" '
if body.get("status") != "executed":
    raise SystemExit("expected executed status")
if body.get("decision_id") is None:
    raise SystemExit("decision_id missing")
'
echo "STEP 6 PASS: purchase executor succeeded with valid token"

echo "purchase-enforcement demo: PASS (decision_id=${DECISION_ID})"
