#!/usr/bin/env bash
# Smoke test: verify deps, config, and that the app starts and stays alive.
# Must be run from the repo root.
set -euo pipefail

PYTHON=".venv/bin/python"

echo "==> Checking venv..."
if [ ! -x "$PYTHON" ]; then
  echo "ERROR: .venv not found. Run: pyenv exec python -m venv .venv && .venv/bin/pip install -r requirements.txt"
  exit 1
fi

echo "==> Checking ctypes (requires libffi-dev + pyenv rebuild)..."
$PYTHON -c "import ctypes" 2>&1 || {
  echo "ERROR: ctypes missing. See Gotchas: rebuild pyenv Python after installing libffi-dev."
  exit 1
}

echo "==> Checking key imports..."
$PYTHON -c "import cv2, mediapipe; print('  cv2', cv2.__version__); print('  mediapipe ok')"

echo "==> Checking config.json..."
if [ ! -f config.json ]; then
  echo "  config.json missing — creating from example"
  cp config.example.json config.json
fi

echo "==> Launching app (DISPLAY=$DISPLAY)..."
DISPLAY="${DISPLAY:-:0}" $PYTHON main.py &
APP_PID=$!
echo "  pid=$APP_PID"

sleep 6

if kill -0 "$APP_PID" 2>/dev/null; then
  echo "==> App is alive after 6s — PASS"
  kill "$APP_PID"
  wait "$APP_PID" 2>/dev/null || true
  echo "==> Done."
else
  echo "ERROR: App exited early — FAIL"
  exit 1
fi
