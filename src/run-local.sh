#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"
root="$(pwd)"
api_host="${API_HOST_BIND:-127.0.0.1}"
api_port="${API_HOST_PORT:-8000}"
ui_host="${UI_HOST_BIND:-127.0.0.1}"
ui_port="${UI_HOST_PORT:-5173}"
python_bin="${PYTHON:-python3}"

if [[ -x "$root/api/venv/bin/python" ]]; then
  python_bin="$root/api/venv/bin/python"
fi

pids=()
cleanup() {
  status=$?
  trap - EXIT INT TERM
  if ((${#pids[@]})); then
    kill "${pids[@]}" 2>/dev/null || true
    wait "${pids[@]}" 2>/dev/null || true
  fi
  exit "$status"
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

(
  cd "$root/api"
  export DATABASE_ENGINE="${DATABASE_ENGINE:-sqlite}"
  "$python_bin" manage.py migrate
  exec "$python_bin" manage.py runserver "$api_host:$api_port"
) &
pids+=("$!")

(
  cd "$root/ui"
  if [[ ! -d node_modules ]]; then
    npm ci
  fi
  export VITE_API_BASE_URL="${VITE_API_BASE_URL:-/api}"
  export VITE_API_PROXY_TARGET="${VITE_API_PROXY_TARGET:-http://127.0.0.1:$api_port}"
  exec npm run dev -- --host "$ui_host" --port "$ui_port"
) &
pids+=("$!")

echo "API: http://127.0.0.1:$api_port/api/health/"
echo "UI: http://127.0.0.1:$ui_port/"
wait -n "${pids[@]}"
