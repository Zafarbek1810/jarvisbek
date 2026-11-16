#!/bin/sh
set -eu
cd "$(dirname "$0")/../.."
.venv/bin/alembic -c backend/alembic.ini upgrade head
exec .venv/bin/uvicorn app.main:app --app-dir backend --host 0.0.0.0 --port 8010
