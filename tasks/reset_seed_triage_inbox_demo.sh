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

if ! command -v curl >/dev/null 2>&1; then
  echo "curl is required" >&2
  exit 1
fi

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
fi

HTTP_CODE="$(curl -sS -o "${TMP_DIR}/seed_response.json" -w "%{http_code}" \
  -X POST "${BASE_URL}/v1/demo/triage_inbox/reset-seed")"

if [[ "${HTTP_CODE}" != "200" ]]; then
  echo "Demo setup failed with HTTP ${HTTP_CODE}" >&2
  cat "${TMP_DIR}/seed_response.json" >&2
  exit 1
fi

if command -v python3 >/dev/null 2>&1; then
  python3 -m json.tool <"${TMP_DIR}/seed_response.json"
else
  cat "${TMP_DIR}/seed_response.json"
fi
