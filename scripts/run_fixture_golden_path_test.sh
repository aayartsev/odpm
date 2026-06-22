#!/usr/bin/env bash
# Run weekly fixture golden-path (in-repo minimal project + Odoo /web HTTP).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

export ODPM_RUN_FIXTURE_GOLDEN_PATH=1
export ODPM_FIXTURE_GOLDEN_TIMEOUT="${ODPM_FIXTURE_GOLDEN_TIMEOUT:-900}"
export ODPM_COMPOSE_SMOKE_TIMEOUT="${ODPM_COMPOSE_SMOKE_TIMEOUT:-900}"

cd "${REPO_ROOT}"
exec python3 -m unittest tests.integration.test_fixture_golden_path -v "$@"
