#!/usr/bin/env bash
# Run compose smoke integration (minimal fixture + odpm --skip-start + docker compose config).
# Mirrors CI compose-smoke job flags (see docs/contributing/ci.md).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

export ODPM_RUN_DOCKER_COMPOSE_SMOKE=1
export ODPM_COMPOSE_SMOKE_TIMEOUT="${ODPM_COMPOSE_SMOKE_TIMEOUT:-900}"

cd "${REPO_ROOT}"

if [[ "${ODPM_COMPOSE_SMOKE_MAILPIT:-0}" == "1" ]]; then
  exec python3 -m unittest tests.integration.test_compose_smoke -v "$@"
fi

exec python3 -m unittest \
  tests.integration.test_compose_smoke.ComposeSmokeIntegrationTests \
  -v "$@"
