#!/usr/bin/env bash
# Deterministic checks for the web target. The agent cannot skip these; the
# workflow runs them after the agent step and records the result.
# Once web/ exists, install from lockfile, lint, and build.
set -euo pipefail

cd "$(git rev-parse --show-toplevel 2>/dev/null || pwd)"

if [ ! -f web/package.json ]; then
  echo "checks(web): web/ not scaffolded yet; nothing to build (ok)"
  exit 0
fi

cd web
echo "checks(web): npm ci"
npm ci --prefer-offline --no-audit --no-fund
echo "checks(web): npm run lint"
npm run lint
echo "checks(web): npm run build"
npm run build
echo "checks(web): ok"
