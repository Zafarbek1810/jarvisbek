#!/bin/sh
set -eu
cd "$(dirname "$0")/../.."
export PYTHONPATH="$PWD/backend"
exec .venv/bin/python -m app.mcp_server
