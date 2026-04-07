#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
PYTHON_BIN="${JD_PYTHON_BIN:-$ROOT_DIR/.venv/bin/python}"
API_PORT="${JD_API_PORT:-8000}"
NGROK_API_PORT="${JD_NGROK_API_PORT:-4040}"
RUNTIME_DIR="${JD_RUNTIME_DIR:-${TMPDIR:-/tmp}/journal-discovery-online-llm-${API_PORT}-${NGROK_API_PORT}}"
API_LOG="${RUNTIME_DIR}/api.log"
NGROK_LOG="${RUNTIME_DIR}/ngrok.log"
API_PID_FILE="${RUNTIME_DIR}/api.pid"
NGROK_PID_FILE="${RUNTIME_DIR}/ngrok.pid"
MODEL_NAME="${JD_OLLAMA_MODEL:-qwen2.5:1.5b}"
PROVIDER_BASE_URL="${JD_PROVIDER_BASE_URL:-http://127.0.0.1:11434/v1}"
PROVIDER_API_KEY="${JD_PROVIDER_API_KEY:-ollama}"
SYNC_GITHUB="${JD_SYNC_GITHUB:-true}"
TIMEOUT_MS="${JD_LLM_TIMEOUT_MS:-60000}"
FETCH_DOAJ="${JD_FETCH_DOAJ:-true}"
RUN_SMOKE_TEST="${JD_RUN_SMOKE_TEST:-true}"
DEPLOY_PAGES="${JD_DEPLOY_PAGES:-true}"
WORKFLOW_NAME="${JD_GITHUB_WORKFLOW:-Manual Refresh and Deploy Journal Discovery}"
GITHUB_REPO="${JD_GITHUB_REPO:-}"

mkdir -p "${RUNTIME_DIR}"

required_commands=(curl gh ngrok)
for command_name in "${required_commands[@]}"; do
  if ! command -v "${command_name}" >/dev/null 2>&1; then
    echo "Missing required command: ${command_name}" >&2
    exit 1
  fi
done

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "Python runtime not found at ${PYTHON_BIN}" >&2
  exit 1
fi

if [[ "${SYNC_GITHUB}" == "true" ]]; then
  gh auth status >/dev/null
fi

ngrok config check >/dev/null

if ! /opt/homebrew/opt/ollama/bin/ollama list 2>/dev/null | awk '{print $1}' | grep -Fx "${MODEL_NAME}" >/dev/null; then
  echo "Ollama model not found locally: ${MODEL_NAME}" >&2
  echo "Available models:" >&2
  /opt/homebrew/opt/ollama/bin/ollama list >&2 || true
  exit 1
fi

is_pid_running() {
  local pid="$1"
  [[ -n "${pid}" ]] && kill -0 "${pid}" >/dev/null 2>&1
}

read_pid_file() {
  local path="$1"
  if [[ -f "${path}" ]]; then
    tr -d '[:space:]' < "${path}"
  fi
}

wait_for_http() {
  local url="$1"
  local attempts="${2:-60}"
  local sleep_seconds="${3:-1}"
  local index
  for ((index = 0; index < attempts; index += 1)); do
    if curl -fsS "${url}" >/dev/null 2>&1; then
      return 0
    fi
    sleep "${sleep_seconds}"
  done
  return 1
}

fetch_tunnel_url() {
  local web_url="http://127.0.0.1:${NGROK_API_PORT}/api/tunnels"
  if ! curl -fsS "${web_url}" >/dev/null 2>&1; then
    return 1
  fi
  curl -fsS "${web_url}" | "${PYTHON_BIN}" -c '
import json, sys
target_port = sys.argv[1]
payload = json.load(sys.stdin)
for tunnel in payload.get("tunnels", []):
    public_url = str(tunnel.get("public_url") or "").strip()
    proto = str(tunnel.get("proto") or "").strip()
    addr = str(((tunnel.get("config") or {}).get("addr")) or "").strip()
    if public_url and proto == "https" and addr.endswith(f":{target_port}"):
        print(public_url)
        break
' "${API_PORT}"
}

start_api() {
  local current_pid
  current_pid="$(read_pid_file "${API_PID_FILE}")"
  if curl -fsS "http://127.0.0.1:${API_PORT}/healthz" >/dev/null 2>&1; then
    echo "Reusing API endpoint already listening on port ${API_PORT}"
    return 0
  fi
  if is_pid_running "${current_pid}" && curl -fsS "http://127.0.0.1:${API_PORT}/healthz" >/dev/null 2>&1; then
    echo "Reusing API process ${current_pid} on port ${API_PORT}"
    return 0
  fi

  : > "${API_LOG}"
  nohup env \
    LLM_PROVIDER_KIND="openai_compatible" \
    LLM_PROVIDER_BASE_URL="${PROVIDER_BASE_URL}" \
    LLM_PROVIDER_API_KEY="${PROVIDER_API_KEY}" \
    LLM_PROVIDER_MODEL="${MODEL_NAME}" \
    "${PYTHON_BIN}" -m uvicorn journal_discovery_llm_api.app:app --host 127.0.0.1 --port "${API_PORT}" --app-dir "${ROOT_DIR}/src" \
    >> "${API_LOG}" 2>&1 &
  echo "$!" > "${API_PID_FILE}"

  if ! wait_for_http "http://127.0.0.1:${API_PORT}/healthz" 90 1; then
    echo "Local API failed to start. Recent log output:" >&2
    tail -n 80 "${API_LOG}" >&2 || true
    exit 1
  fi
}

start_ngrok() {
  local tunnel_url
  tunnel_url="$(fetch_tunnel_url || true)"
  if [[ -n "${tunnel_url}" ]]; then
    echo "${tunnel_url}"
    return 0
  fi

  local current_pid
  current_pid="$(read_pid_file "${NGROK_PID_FILE}")"
  if is_pid_running "${current_pid}"; then
    echo "ngrok PID ${current_pid} is running but no tunnel URL was discovered; restarting."
    kill "${current_pid}" >/dev/null 2>&1 || true
    rm -f "${NGROK_PID_FILE}"
    sleep 1
  fi

  : > "${NGROK_LOG}"
  nohup ngrok http "${API_PORT}" >> "${NGROK_LOG}" 2>&1 &
  echo "$!" > "${NGROK_PID_FILE}"

  local attempts
  for ((attempts = 0; attempts < 90; attempts += 1)); do
    tunnel_url="$(fetch_tunnel_url || true)"
    if [[ -n "${tunnel_url}" ]]; then
      echo "${tunnel_url}"
      return 0
    fi
    sleep 1
  done

  echo "ngrok failed to expose a public HTTPS URL. Recent log output:" >&2
  tail -n 80 "${NGROK_LOG}" >&2 || true
  exit 1
}

if [[ "${SYNC_GITHUB}" == "true" && -z "${GITHUB_REPO}" ]]; then
  GITHUB_REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
fi

start_api
PUBLIC_URL="$(start_ngrok)"

if [[ "${SYNC_GITHUB}" == "true" ]]; then
  gh variable set LLM_API_BASE_URL --body "${PUBLIC_URL}" --repo "${GITHUB_REPO}"
  gh variable set LLM_TIMEOUT_MS --body "${TIMEOUT_MS}" --repo "${GITHUB_REPO}"
  gh variable set LLM_ABSTRACT_MATCH_ENABLED --body true --repo "${GITHUB_REPO}"
  WORKFLOW_URL="$(gh workflow run "${WORKFLOW_NAME}" --repo "${GITHUB_REPO}" -f fetch_doaj="${FETCH_DOAJ}" -f run_smoke_test="${RUN_SMOKE_TEST}" -f deploy_pages="${DEPLOY_PAGES}")"
fi

echo
echo "Online LLM bridge is running."
echo "Model: ${MODEL_NAME}"
echo "Local API: http://127.0.0.1:${API_PORT}/healthz"
echo "Public LLM URL: ${PUBLIC_URL}"
echo "API log: ${API_LOG}"
echo "ngrok log: ${NGROK_LOG}"
echo "Stop command: scripts/stop_online_llm_bridge.sh"

if [[ "${SYNC_GITHUB}" == "true" ]]; then
  echo "GitHub repo: ${GITHUB_REPO}"
  echo "Triggered workflow: ${WORKFLOW_NAME}"
  echo "Workflow run: ${WORKFLOW_URL}"
  echo "Watch with: gh run watch --repo ${GITHUB_REPO} \$(basename \"${WORKFLOW_URL}\")"
else
  echo "GitHub sync skipped because JD_SYNC_GITHUB=${SYNC_GITHUB}"
fi
