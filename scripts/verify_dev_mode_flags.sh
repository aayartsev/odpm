#!/usr/bin/env bash
# Verify every Odoo --dev flag on a real odpm project (opt-in, slow).
#
# Runs:
#   1. test_all_dev_mode_flags_compose — odpm --skip-start + compose --dev (13 cases)
#   2. test_all_dev_mode_flags_live — docker up/down + HTTP (requires stack down)
#   3. scripts/verify_dev_mode_autoreload.sh — save .py with dev_mode=all (reload probe)
#
# Example:
#   docker compose down   # in project dir, required for live phase
#   ODPM_GOLDEN_PATH_PROJECT=/path/to/project ./scripts/verify_dev_mode_flags.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -z "${ODPM_GOLDEN_PATH_PROJECT:-}" ]]; then
    echo "Set ODPM_GOLDEN_PATH_PROJECT to an initialized odpm project directory." >&2
    echo "Example: ODPM_GOLDEN_PATH_PROJECT=/path/to/demo-project $0" >&2
    exit 1
fi

export ODPM_RUN_DOCKER_INTEGRATION=1
export ODPM_ODPM_PY="${ODPM_ODPM_PY:-${REPO_ROOT}/odpm.py}"

cd "${REPO_ROOT}"
exec python3 -m unittest tests.integration.test_dev_mode_flags -v "$@"
