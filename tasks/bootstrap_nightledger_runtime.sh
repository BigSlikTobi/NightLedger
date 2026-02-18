#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${ROOT_DIR}/.venv/bin/python"
UVICORN_MODULE="uvicorn"
API_APP="nightledger_api.main:app"
MCP_APP="nightledger_api.mcp_remote_server:app"
API_HOST="${NIGHTLEDGER_API_HOST:-127.0.0.1}"
API_PORT="${NIGHTLEDGER_API_PORT:-8001}"
MCP_HOST="${NIGHTLEDGER_MCP_HOST:-127.0.0.1}"
MCP_PORT="${NIGHTLEDGER_MCP_PORT:-8002}"
MCP_AUTH_TOKEN="${NIGHTLEDGER_MCP_REMOTE_AUTH_TOKEN:-nightledger-local-dev-token}"
DRY_RUN=0

if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
fi

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Missing ${PYTHON_BIN}. Run python -m venv .venv and install requirements first." >&2
  exit 1
fi

API_CMD=( "${PYTHON_BIN}" -m "${UVICORN_MODULE}" "${API_APP}" --host "${API_HOST}" --port "${API_PORT}" )
MCP_CMD=( "${PYTHON_BIN}" -m "${UVICORN_MODULE}" "${MCP_APP}" --host "${MCP_HOST}" --port "${MCP_PORT}" )

echo "NIGHTLEDGER_MCP_REMOTE_AUTH_TOKEN=${MCP_AUTH_TOKEN}"
echo "PYTHONPATH=${ROOT_DIR}src ${API_CMD[*]}"
echo "PYTHONPATH=${ROOT_DIR}src NIGHTLEDGER_MCP_REMOTE_AUTH_TOKEN=${MCP_AUTH_TOKEN} ${MCP_CMD[*]}"

if [[ "${DRY_RUN}" -eq 1 ]]; then
  exit 0
fi

API_PID=""
MCP_PID=""

cleanup() {
  if [[ -n "${API_PID}" ]] && kill -0 "${API_PID}" 2>/dev/null; then
    kill "${API_PID}" 2>/dev/null || true
  fi
  if [[ -n "${MCP_PID}" ]] && kill -0 "${MCP_PID}" 2>/dev/null; then
    kill "${MCP_PID}" 2>/dev/null || true
  fi
}

trap cleanup EXIT INT TERM

(
  cd "${ROOT_DIR}"
  PYTHONPATH="${ROOT_DIR}/src" "${API_CMD[@]}"
) &
API_PID="$!"

(
  cd "${ROOT_DIR}"
  PYTHONPATH="${ROOT_DIR}/src" NIGHTLEDGER_MCP_REMOTE_AUTH_TOKEN="${MCP_AUTH_TOKEN}" "${MCP_CMD[@]}"
) &
MCP_PID="$!"

echo "NightLedger API running on http://${API_HOST}:${API_PORT}"
echo "NightLedger MCP remote running on http://${MCP_HOST}:${MCP_PORT}/v1/mcp/remote"
echo "Press Ctrl+C to stop both processes."

wait "${API_PID}" "${MCP_PID}"
