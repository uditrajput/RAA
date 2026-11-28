#!/usr/bin/env bash
set -euo pipefail

# ============================================================================
# RAA Launcher for Linux & macOS (Setup UI + MCP Server)
# Usage:
#   ./scripts/start_raa.sh              Start both Setup UI and MCP HTTP server
#   ./scripts/start_raa.sh --ui-only    Start Setup UI only
#   ./scripts/start_raa.sh --mcp-only   Start MCP HTTP server only
#   ./scripts/start_raa.sh --mcp-stdio  Start MCP server in stdio mode (foreground)
#   ./scripts/start_raa.sh --no-open    Do not auto-open browser
# ============================================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$REPO_ROOT"

UI_HOST="${UI_HOST:-127.0.0.1}"
UI_PORT="${UI_PORT:-8765}"
MCP_HOST="${MCP_HOST:-127.0.0.1}"
MCP_PORT="${MCP_PORT:-8766}"
MCP_TRANSPORT="${MCP_TRANSPORT:-http}"

RUN_UI=1
RUN_MCP=1
OPEN_BROWSER=1

for arg in "$@"; do
  case "$arg" in
    --ui-only)
      RUN_MCP=0
      ;;
    --mcp-only)
      RUN_UI=0
      ;;
    --mcp-stdio)
      RUN_UI=0
      MCP_TRANSPORT="stdio"
      OPEN_BROWSER=0
      ;;
    --no-open)
      OPEN_BROWSER=0
      ;;
    -h|--help)
      echo "Usage: $0 [--ui-only | --mcp-only | --mcp-stdio] [--no-open]"
      exit 0
      ;;
    *)
      echo "Unknown option: $arg" >&2
      exit 1
      ;;
  esac
done

if [ -x "$REPO_ROOT/.venv/bin/python" ]; then
  PYTHON_BIN="$REPO_ROOT/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PYTHON_BIN="python3"
elif command -v python >/dev/null 2>&1; then
  PYTHON_BIN="python"
else
  echo "[ERROR] Neither .venv/bin/python nor python3/python was found." >&2
  exit 1
fi

if [ "$MCP_TRANSPORT" = "stdio" ]; then
  exec "$PYTHON_BIN" -m raa.cli.main serve mcp --transport stdio
fi

PIDS=()

cleanup() {
  trap - INT TERM EXIT
  for pid in "${PIDS[@]:-}"; do
    if kill -0 "$pid" 2>/dev/null; then
      kill "$pid" 2>/dev/null || true
    fi
  done
  wait 2>/dev/null || true
}
trap cleanup INT TERM EXIT

echo "[RAA] Using Python: $PYTHON_BIN"
echo "[RAA] Workspace:    $REPO_ROOT"

if [ "$RUN_UI" -eq 1 ]; then
  echo "[RAA] Starting Setup UI & API at http://${UI_HOST}:${UI_PORT}/setup ..."
  "$PYTHON_BIN" -m raa.cli.main serve api --host "$UI_HOST" --port "$UI_PORT" &
  PIDS+=("$!")
fi

if [ "$RUN_MCP" -eq 1 ]; then
  echo "[RAA] Starting MCP Server (${MCP_TRANSPORT}) at http://${MCP_HOST}:${MCP_PORT}/mcp ..."
  "$PYTHON_BIN" -m raa.cli.main serve mcp --transport "$MCP_TRANSPORT" --host "$MCP_HOST" --port "$MCP_PORT" &
  PIDS+=("$!")
fi

if [ "$RUN_UI" -eq 1 ] && [ "$OPEN_BROWSER" -eq 1 ]; then
  sleep 2
  URL="http://${UI_HOST}:${UI_PORT}/setup"
  case "$(uname -s)" in
    Darwin)
      open "$URL" >/dev/null 2>&1 || true
      ;;
    Linux)
      if command -v xdg-open >/dev/null 2>&1; then
        xdg-open "$URL" >/dev/null 2>&1 || true
      fi
      ;;
  esac
fi

echo "[RAA] Running. Press Ctrl+C to stop."
wait
