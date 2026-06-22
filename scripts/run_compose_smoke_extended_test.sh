#!/usr/bin/env bash
# Run plugin + hooks integration E2E (compose-smoke matrix extensions).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

export ODPM_RUN_DOCKER_COMPOSE_SMOKE=1
export ODPM_COMPOSE_SMOKE_PLUGIN=1
export ODPM_COMPOSE_SMOKE_HOOKS=1
export ODPM_COMPOSE_SMOKE_TIMEOUT="${ODPM_COMPOSE_SMOKE_TIMEOUT:-900}"

cd "${REPO_ROOT}"
python3 -m pip install -q -e tests/fixtures/sample_plugin
exec python3 -m unittest \
  tests.integration.test_plugin_compose_e2e \
  tests.integration.test_hooks_integration_e2e \
  -v "$@"
