#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/backend"
command -v python3 >/dev/null || { echo "Install Python 3.10-3.12 first"; exit 1; }
[ -d .venv ] || python3 -m venv .venv
source .venv/bin/activate
if [ ! -f .venv/installed.flag ]; then
  echo "Installing packages - the first time takes several minutes..."
  pip install torch --index-url https://download.pytorch.org/whl/cpu
  pip install -r requirements.txt
  touch .venv/installed.flag
fi
(sleep 5; (open http://localhost:8000 || xdg-open http://localhost:8000) >/dev/null 2>&1) &
echo "Starting SmartAudit AI at http://localhost:8000  (Ctrl+C to stop)"
uvicorn app.main:app --port 8000
