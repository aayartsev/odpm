#!/usr/bin/env bash
# Create an ephemeral odpm project wrapper for golden-path (ADR-006).
#
# Default: mktemp under /tmp (or TMPDIR / ODPM_GOLDEN_PATH_TMP_ROOT). Git clones
# and Docker images stay in the runner user home (ODOO_PROJECTS_DIR / docker).
# Optional: if ODPM_GOLDEN_PATH_PROJECT already points at a prepared tree
# (docker-compose.yml present), reuse it for backward compatibility.
#
# Prints the project path on stdout (capture into ODPM_GOLDEN_PATH_PROJECT).
# Logs go to stderr.
set -euo pipefail

log() {
    echo "[golden-path bootstrap $(date -u +%Y-%m-%dT%H:%M:%SZ)] $*" >&2
}

MAJOR="${ODPM_GOLDEN_PATH_MAJOR:-19}"
if [[ ! "${MAJOR}" =~ ^[0-9]+$ ]]; then
    echo "ODPM_GOLDEN_PATH_MAJOR must be numeric (got '${MAJOR}')" >&2
    exit 1
fi

DEMO_URL="${ODPM_GOLDEN_PATH_DEMO_URL:-https://github.com/aayartsev/odoo_demo_project.git}"
DEMO_BRANCH="${ODPM_GOLDEN_PATH_DEMO_BRANCH:-${MAJOR}.0}"

if [[ -n "${ODPM_GOLDEN_PATH_PROJECT:-}" ]]; then
    if [[ -f "${ODPM_GOLDEN_PATH_PROJECT}/docker-compose.yml" ]]; then
        log "reusing existing project ${ODPM_GOLDEN_PATH_PROJECT}"
        printf '%s\n' "${ODPM_GOLDEN_PATH_PROJECT}"
        exit 0
    fi
    log "ODPM_GOLDEN_PATH_PROJECT=${ODPM_GOLDEN_PATH_PROJECT} has no docker-compose.yml; bootstrapping ephemeral wrapper instead"
fi

if ! command -v odpm >/dev/null 2>&1; then
    echo "odpm not found on PATH; install odpm before golden-path bootstrap" >&2
    exit 1
fi

TMP_ROOT="${ODPM_GOLDEN_PATH_TMP_ROOT:-${TMPDIR:-/tmp}}"
TMP_ROOT="${TMP_ROOT%/}"
mkdir -p "${TMP_ROOT}"
PROJECT="$(mktemp -d "${TMP_ROOT}/odpm-golden-${MAJOR}.XXXXXX")"
log "ephemeral project=${PROJECT} major=${MAJOR} branch=${DEMO_BRANCH}"
log "odpm=$(command -v odpm); $(odpm --version 2>&1 | head -1)"

cd "${PROJECT}"
log "odpm init ${DEMO_URL} --branch ${DEMO_BRANCH} ..."
# Non-interactive: home ~/.odpm should already exist on the self-hosted runner
# (ODOO_PROJECTS_DIR / BACKUP_DIR). Init materializes developing + prepare.
odpm init "${DEMO_URL}" --branch "${DEMO_BRANCH}"
log "odpm init done"

if [[ ! -f "${PROJECT}/docker-compose.yml" ]]; then
    echo "bootstrap failed: missing docker-compose.yml in ${PROJECT}" >&2
    exit 1
fi

printf '%s\n' "${PROJECT}"
