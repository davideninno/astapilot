#!/bin/sh
uvicorn app.main:app --app-dir /app/backend --host 0.0.0.0 --port ${PORT:-8000}
