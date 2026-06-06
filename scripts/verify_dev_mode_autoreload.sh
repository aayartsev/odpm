#!/usr/bin/env bash
# Opt-in: verify Odoo autoreload with dev_mode=all after saving a .py file.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -z "${ODPM_GOLDEN_PATH_PROJECT:-}" ]]; then
    echo "Set ODPM_GOLDEN_PATH_PROJECT to an initialized odpm project directory." >&2
    exit 1
fi

export ODPM_RUN_DOCKER_INTEGRATION=1
export ODPM_ODPM_PY="${ODPM_ODPM_PY:-${REPO_ROOT}/odpm.py}"

cd "${REPO_ROOT}"
exec python3 -m unittest \
    tests.integration.test_dev_mode_flags.DevModeAutoreloadIntegrationTests -v "$@"
