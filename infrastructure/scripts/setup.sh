#!/bin/sh
set -eu
cd "$(dirname "$0")/../.."
if [ ! -f .env ]; then
  python3 - <<'PY'
from pathlib import Path
import secrets
Path('.env').write_text(Path('.env.example').read_text().replace('replace-with-a-random-secret-of-at-least-32-characters', secrets.token_urlsafe(48)))
PY
fi
chmod 600 .env
python3.12 -m venv .venv
.venv/bin/pip install -r backend/requirements.lock.txt
npm ci
printf '%s\n' 'Tayyor. PostgreSQL va Redis xizmatlarini ishga tushiring, so‘ng migratsiyani bajaring.'
