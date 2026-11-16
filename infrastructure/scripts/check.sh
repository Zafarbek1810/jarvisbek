#!/bin/sh
set -eu
cd "$(dirname "$0")/../.."
.venv/bin/pytest backend/tests -q
npm run typecheck
npm run lint
npm test
npm run build
