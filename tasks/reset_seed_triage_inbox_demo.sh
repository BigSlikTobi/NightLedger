#!/usr/bin/env bash
set -euo pipefail

BASE_URL="${BASE_URL:-http://127.0.0.1:8001}"
AUTO_START="${AUTO_START:-1}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
VENV_PYTHON="${REPO_ROOT}/.venv/bin/python"
TMP_DIR="$(mktemp -d)"
API_PID=""

BASE_URL_HOST=""
BASE_URL_PORT=""

parse_base_url_host_port() {
  local url="$1"
  python3 - "$url" <<'PY'
import sys
from urllib.parse import urlparse

url = sys.argv[1]
parsed = urlparse(url)

if parsed.scheme not in {"http", "https"}:
  raise SystemExit("BASE_URL must use http or https")
if not parsed.hostname:
  raise SystemExit("BASE_URL must include a hostname")
if parsed.path not in {"", "/"} or parsed.params or parsed.query or parsed.fragment:
  raise SystemExit("BASE_URL must not include path, query, or fragment")

default_port = 443 if parsed.scheme == "https" else 80
port = parsed.port or default_port
print(parsed.hostname)
print(port)
PY
}

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

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 is required" >&2
  exit 1
fi

if ! mapfile -t BASE_URL_PARTS < <(parse_base_url_host_port "${BASE_URL}"); then
  echo "Invalid BASE_URL: ${BASE_URL}" >&2
  echo "Expected format: http(s)://host[:port]" >&2
  exit 1
fi

if [[ "${#BASE_URL_PARTS[@]}" -ne 2 ]]; then
  echo "Failed to parse BASE_URL: ${BASE_URL}" >&2
  exit 1
fi

BASE_URL_HOST="${BASE_URL_PARTS[0]}"
BASE_URL_PORT="${BASE_URL_PARTS[1]}"

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
    --host "${BASE_URL_HOST}" --port "${BASE_URL_PORT}" >"${TMP_DIR}/api.log" 2>&1 &
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
