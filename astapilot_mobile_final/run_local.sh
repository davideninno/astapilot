#!/bin/sh
set -e
cd "$(dirname "$0")/backend"
export PYTHONPATH=.
export ASTAPILOT_DB="${ASTAPILOT_DB:-$(pwd)/../astapilot.sqlite3}"
exec uvicorn app.main:app --host 0.0.0.0 --port "${PORT:-8000}"
