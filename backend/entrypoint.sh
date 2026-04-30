#!/bin/sh
set -e

echo "Running Alembic migrations..."
alembic upgrade head || { echo "FATAL: alembic upgrade head failed — aborting startup"; exit 1; }

echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
