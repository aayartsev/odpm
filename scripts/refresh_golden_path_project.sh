#!/usr/bin/env bash
# Refresh long-lived ODPM_GOLDEN_PATH_PROJECT (odpm --skip-start).
# With ODPM_GOLDEN_PATH_AUTO_REMEDIATE=1, remedi ate only when schema is incompatible
# (odpm -i / wipe on failure). Pre-release CI enables this; job budget ≈9 min.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=golden_path_project_lib.sh
source "${SCRIPT_DIR}/golden_path_project_lib.sh"

log() {
    echo "[golden-path refresh $(date -u +%Y-%m-%dT%H:%M:%SZ)] $*"
}

PROJECT="${ODPM_GOLDEN_PATH_PROJECT:?Set ODPM_GOLDEN_PATH_PROJECT}"
# Default off for local/ad-hoc. Release golden-path sets AUTO_REMEDIATE=1.
AUTO_REMEDIATE="${ODPM_GOLDEN_PATH_AUTO_REMEDIATE:-0}"

if [[ ! -d "${PROJECT}" ]]; then
    echo "ODPM_GOLDEN_PATH_PROJECT is not a directory: ${PROJECT}" >&2
    exit 1
fi

if [[ ! -f "${PROJECT}/docker-compose.yml" ]]; then
    echo "Missing docker-compose.yml in ${PROJECT}" >&2
    exit 1
fi

if ! command -v odpm >/dev/null 2>&1; then
    echo "odpm not found on PATH; install the built .deb before refresh" >&2
    exit 1
fi

SECONDS=0
log "start project=${PROJECT} AUTO_REMEDIATE=${AUTO_REMEDIATE}"
log "odpm=$(command -v odpm); $(odpm --version 2>&1 | head -1)"

REPO_ROOT="$(golden_path_repo_root)"
POSTGRES_SERVICE="$(golden_path_postgres_service "${PROJECT}" "${REPO_ROOT}")"
PGUSER="$(golden_path_read_env "${PROJECT}" POSTGRES_ODOO_USER odoo)"
PGPASSWORD="$(golden_path_read_env "${PROJECT}" POSTGRES_ODOO_PASS odoo)"
export PGPASSWORD
DB_NAME="$(golden_path_read_env "${PROJECT}" ODOO_DB_NAME test_db)"

cd "${PROJECT}"
log "docker compose down --remove-orphans ..."
docker compose down --remove-orphans 2>/dev/null || true
log "docker compose down done (${SECONDS}s elapsed)"

log "odpm --skip-start --no-git-update ..."
odpm --skip-start --no-git-update
log "odpm --skip-start done (${SECONDS}s elapsed)"
log "Golden-path project refreshed with $(odpm --version 2>&1 | head -1)"
ODOO_MANIFEST_VERSION="$(golden_path_odoo_version_from_manifest "${PROJECT}" || true)"
if [[ -n "${ODOO_MANIFEST_VERSION}" ]]; then
    log "odpm.json odoo_version=${ODOO_MANIFEST_VERSION}"
fi

if [[ "${AUTO_REMEDIATE}" == "0" || "${AUTO_REMEDIATE}" == "false" ]]; then
    log "ODPM_GOLDEN_PATH_AUTO_REMEDIATE=${AUTO_REMEDIATE}; skipping DB schema check."
    exit 0
fi

log "ensure postgres up (service=${POSTGRES_SERVICE}) ..."
golden_path_ensure_postgres_up "${PROJECT}" "${POSTGRES_SERVICE}" "${PGUSER}"
trap 'cd "${PROJECT}" && docker compose down --remove-orphans 2>/dev/null || true' EXIT

if golden_path_database_exists "${POSTGRES_SERVICE}" "${PGUSER}" "${DB_NAME}"; then
    golden_path_log_short_time_gate "${PROJECT}" "${POSTGRES_SERVICE}" "${PGUSER}" "${DB_NAME}"
fi

if golden_path_database_exists "${POSTGRES_SERVICE}" "${PGUSER}" "${DB_NAME}" \
    && golden_path_schema_compatible "${POSTGRES_SERVICE}" "${PGUSER}" "${DB_NAME}"; then
    log "DB ${DB_NAME} ready ($(golden_path_schema_status_line "${POSTGRES_SERVICE}" "${PGUSER}" "${DB_NAME}"))."
    exit 0
fi

if golden_path_database_exists "${POSTGRES_SERVICE}" "${PGUSER}" "${DB_NAME}"; then
    log "DB ${DB_NAME} not ready ($(golden_path_schema_status_line "${POSTGRES_SERVICE}" "${PGUSER}" "${DB_NAME}")); remediating..."
else
    log "DB ${DB_NAME} missing; initializing..."
fi

golden_path_remediate_database "${PROJECT}" "${DB_NAME}" "${POSTGRES_SERVICE}" "${PGUSER}"

log "re-check schema after remedi ate ..."
golden_path_ensure_postgres_up "${PROJECT}" "${POSTGRES_SERVICE}" "${PGUSER}"
if ! golden_path_schema_compatible "${POSTGRES_SERVICE}" "${PGUSER}" "${DB_NAME}"; then
    log "DB ${DB_NAME} still not ready ($(golden_path_schema_status_line "${POSTGRES_SERVICE}" "${PGUSER}" "${DB_NAME}")); wiping postgres volume and retrying..."
    golden_path_remediate_database "${PROJECT}" "${DB_NAME}" "${POSTGRES_SERVICE}" "${PGUSER}" 1
    golden_path_ensure_postgres_up "${PROJECT}" "${POSTGRES_SERVICE}" "${PGUSER}"
fi
if ! golden_path_schema_compatible "${POSTGRES_SERVICE}" "${PGUSER}" "${DB_NAME}"; then
    golden_path_emit_schema_failure "${PROJECT}" "${DB_NAME}" "${POSTGRES_SERVICE}" "${PGUSER}"
    exit 1
fi

log "DB ${DB_NAME} ready ($(golden_path_schema_status_line "${POSTGRES_SERVICE}" "${PGUSER}" "${DB_NAME}"))."
