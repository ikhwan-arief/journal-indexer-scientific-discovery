#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${JD_PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"
API_PORT="${JD_API_PORT:-8000}"
NGROK_API_PORT="${JD_NGROK_API_PORT:-4040}"
RUNTIME_DIR="${JD_RUNTIME_DIR:-${TMPDIR:-/tmp}/journal-discovery-online-llm-${API_PORT}-${NGROK_API_PORT}}"
API_PID_FILE="${RUNTIME_DIR}/api.pid"
NGROK_PID_FILE="${RUNTIME_DIR}/ngrok.pid"
SYNC_GITHUB="${JD_SYNC_GITHUB:-true}"
WORKFLOW_NAME="${JD_GITHUB_WORKFLOW:-Manual Refresh and Deploy Journal Discovery}"
GITHUB_REPO="${JD_GITHUB_REPO:-}"
FETCH_DOAJ="${JD_FETCH_DOAJ:-true}"
RUN_SMOKE_TEST="${JD_RUN_SMOKE_TEST:-true}"
DEPLOY_PAGES="${JD_DEPLOY_PAGES:-true}"

required_commands=(gh)
if [[ "${SYNC_GITHUB}" == "true" ]]; then
  for command_name in "${required_commands[@]}"; do
    if ! command -v "${command_name}" >/dev/null 2>&1; then
      echo "Missing required command: ${command_name}" >&2
      exit 1
    fi
  done
  gh auth status >/dev/null
fi

if [[ -z "${GITHUB_REPO}" && "${SYNC_GITHUB}" == "true" ]]; then
  GITHUB_REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
fi

stop_from_pid_file() {
  local name="$1"
  local path="$2"
  if [[ ! -f "${path}" ]]; then
    echo "${name}: no pid file"
    return 0
  fi

  local pid
  pid="$(tr -d '[:space:]' < "${path}")"
  if [[ -n "${pid}" ]] && kill -0 "${pid}" >/dev/null 2>&1; then
    kill "${pid}" >/dev/null 2>&1 || true
    echo "${name}: stopped pid ${pid}"
  else
    echo "${name}: process already stopped"
  fi
  rm -f "${path}"
}

stop_from_pid_file "API" "${API_PID_FILE}"
stop_from_pid_file "ngrok" "${NGROK_PID_FILE}"

if [[ "${SYNC_GITHUB}" == "true" ]]; then
  gh variable delete LLM_API_BASE_URL --repo "${GITHUB_REPO}" >/dev/null 2>&1 || true
  gh variable set LLM_ABSTRACT_MATCH_ENABLED --body false --repo "${GITHUB_REPO}"
  WORKFLOW_URL="$(gh workflow run "${WORKFLOW_NAME}" --repo "${GITHUB_REPO}" -f fetch_doaj="${FETCH_DOAJ}" -f run_smoke_test="${RUN_SMOKE_TEST}" -f deploy_pages="${DEPLOY_PAGES}")"
  echo "Disabled online LLM config in ${GITHUB_REPO}"
  echo "Triggered workflow: ${WORKFLOW_NAME}"
  echo "Workflow run: ${WORKFLOW_URL}"
else
  echo "GitHub sync skipped because JD_SYNC_GITHUB=${SYNC_GITHUB}"
fi
