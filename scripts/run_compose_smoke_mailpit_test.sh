#!/usr/bin/env bash
# Run compose smoke with Mailpit manifest v2 step (CI parity).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

export ODPM_RUN_DOCKER_COMPOSE_SMOKE=1
export ODPM_COMPOSE_SMOKE_MAILPIT=1
export ODPM_COMPOSE_SMOKE_TIMEOUT="${ODPM_COMPOSE_SMOKE_TIMEOUT:-900}"

cd "${REPO_ROOT}"
exec python3 -m unittest \
  tests.integration.test_compose_smoke.ComposeSmokeMailpitIntegrationTests \
  -v "$@"
