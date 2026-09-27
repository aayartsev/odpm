#!/usr/bin/env bash
# Run opt-in golden-path E2E from any cwd (requires ODPM_GOLDEN_PATH_PROJECT).
# Mirrors CI golden-path job: refresh (odpm --skip-start) → preflight → unittest
# (ADR-006 / docs/contributing/ci.md).
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
export ODPM_GOLDEN_PATH_TIMEOUT="${ODPM_GOLDEN_PATH_TIMEOUT:-60}"
export ODPM_COMPOSE_DEBUG_DIR="${ODPM_COMPOSE_DEBUG_DIR:-}"
# Local default off; CI sets ODPM_GOLDEN_PATH_AUTO_REMEDIATE=1 on the refresh step.
export ODPM_GOLDEN_PATH_AUTO_REMEDIATE="${ODPM_GOLDEN_PATH_AUTO_REMEDIATE:-0}"

# Prefer installed odpm; otherwise wrap the repo entrypoint for refresh/preflight.
if ! command -v odpm >/dev/null 2>&1; then
    if [[ ! -f "${ODPM_ODPM_PY}" ]]; then
        echo "odpm not on PATH and ODPM_ODPM_PY missing: ${ODPM_ODPM_PY}" >&2
        exit 1
    fi
    _odpm_bindir="$(mktemp -d "${TMPDIR:-/tmp}/odpm-golden-bin.XXXXXX")"
    cat > "${_odpm_bindir}/odpm" <<EOF
#!/usr/bin/env bash
exec python3 "${ODPM_ODPM_PY}" "\$@"
EOF
    chmod +x "${_odpm_bindir}/odpm"
    export PATH="${_odpm_bindir}:${PATH}"
fi

cd "${REPO_ROOT}"

if [[ "${ODPM_GOLDEN_PATH_SKIP_REFRESH:-0}" != "1" ]]; then
    echo "[golden-path] refresh_golden_path_project.sh ..."
    bash "${SCRIPT_DIR}/refresh_golden_path_project.sh"
    echo "[golden-path] preflight_golden_path_project.sh ..."
    bash "${SCRIPT_DIR}/preflight_golden_path_project.sh"
fi

exec python3 -m unittest tests.integration.test_golden_path -v "$@"
