#!/usr/bin/env bash
# Run opt-in golden-path E2E from any cwd (requires ODPM_GOLDEN_PATH_PROJECT).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

if [[ -z "${ODPM_GOLDEN_PATH_PROJECT:-}" ]]; then
    echo "Set ODPM_GOLDEN_PATH_PROJECT to an initialized odpm project directory." >&2
    echo "Example: ODPM_GOLDEN_PATH_PROJECT=/path/to/your-odpm-env $0" >&2
    exit 1
fi

export ODPM_RUN_DOCKER_INTEGRATION=1
export ODPM_ODPM_PY="${ODPM_ODPM_PY:-${REPO_ROOT}/odpm.py}"
export ODPM_GOLDEN_PATH_TIMEOUT="${ODPM_GOLDEN_PATH_TIMEOUT:-300}"

cd "${REPO_ROOT}"
exec python3 -m unittest tests.integration.test_golden_path -v "$@"
