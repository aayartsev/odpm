#!/usr/bin/env bash
# Refresh ODPM_GOLDEN_PATH_PROJECT (odpm prepare).
# Project may be a long-lived path or an ephemeral /tmp wrapper from
# bootstrap_golden_path_project.sh (git/images stay under the runner home).
# With ODPM_GOLDEN_PATH_AUTO_REMEDIATE=1, remedi ate only when schema is incompatible
# (odpm -i / wipe on failure). Pre-release CI enables this; job budget ≈15 min.
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

# Allow git materialize/checkout so platform follows odpm.json odoo_version.
# --no-git-update left a drifted checkout (wrong branch/requirements) and
# broke /web with ModuleNotFoundError. Opt out offline with
# ODPM_GOLDEN_PATH_NO_GIT_UPDATE=1.
GOLDEN_PATH_ODPM_GIT_FLAGS=()
if [[ "${ODPM_GOLDEN_PATH_NO_GIT_UPDATE:-0}" == "1" ]]; then
    GOLDEN_PATH_ODPM_GIT_FLAGS+=(--no-git-update)
    log "ODPM_GOLDEN_PATH_NO_GIT_UPDATE=1; skipping git materialize/checkout"
fi

# Always bake -d into compose: early "DB ready" exits skip remedi ate, and without
# -d unittest compose up leaves multi-db idle HTTP (403 on /web/login).
log "odpm prepare ${GOLDEN_PATH_ODPM_GIT_FLAGS[*]:-} -d ${DB_NAME} ..."
odpm prepare "${GOLDEN_PATH_ODPM_GIT_FLAGS[@]}" -d "${DB_NAME}" \
    "${GOLDEN_PATH_ODPM_ACCEPT_DRIFT[@]}"
log "odpm prepare done (${SECONDS}s elapsed)"
# odpm may rewrite docker-compose.yml (e.g. legacy POSTGRES_SERVICE_NAME=db-dev → db).
POSTGRES_SERVICE="$(golden_path_postgres_service "${PROJECT}" "${REPO_ROOT}")"
log "postgres compose service=${POSTGRES_SERVICE}"
log "Golden-path project refreshed with $(odpm --version 2>&1 | head -1)"
ODOO_MANIFEST_VERSION="$(golden_path_odoo_version_from_manifest "${PROJECT}" || true)"
if [[ -n "${ODOO_MANIFEST_VERSION}" ]]; then
    log "odpm.json odoo_version=${ODOO_MANIFEST_VERSION}"
fi

if [[ "${AUTO_REMEDIATE}" == "0" || "${AUTO_REMEDIATE}" == "false" ]]; then
    log "ODPM_GOLDEN_PATH_AUTO_REMEDIATE=${AUTO_REMEDIATE}; skipping DB schema check."
    exit 0
fi

ODOO_MAJOR="$(golden_path_odoo_major "${ODOO_MANIFEST_VERSION}" || true)"
if [[ -z "${ODOO_MANIFEST_VERSION}" || -z "${ODOO_MAJOR}" ]]; then
    echo "::error::Golden-path needs a numeric odpm.json odoo_version (e.g. 19.0 or 20.0); got '${ODOO_MANIFEST_VERSION:-missing}'." >&2
    echo "Use one directory per Odoo major (docs/contributing/demo-projects.md)." >&2
    echo "Fix ODPM_GOLDEN_PATH_PROJECT (or its odpm.json) on the self-hosted runner." >&2
    exit 1
fi
log "golden-path schema major=${ODOO_MAJOR} (from odpm.json; one catalog per major)"

log "ensure postgres up (service=${POSTGRES_SERVICE}) ..."
if ! golden_path_ensure_postgres_up "${PROJECT}" "${POSTGRES_SERVICE}" "${PGUSER}"; then
    # Accepting postgres_major updates last_run.json but does not migrate the data
    # directory; an old PG_VERSION leaves the new image crash-looping.
    log "Postgres not ready after refresh; wiping postgres volume and remediating..."
    golden_path_remediate_database "${PROJECT}" "${DB_NAME}" "${POSTGRES_SERVICE}" "${PGUSER}" 1
    POSTGRES_SERVICE="$(golden_path_postgres_service "${PROJECT}" "${REPO_ROOT}")"
    golden_path_ensure_postgres_up "${PROJECT}" "${POSTGRES_SERVICE}" "${PGUSER}"
fi
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
POSTGRES_SERVICE="$(golden_path_postgres_service "${PROJECT}" "${REPO_ROOT}")"

log "re-check schema after remedi ate (service=${POSTGRES_SERVICE}) ..."
golden_path_ensure_postgres_up "${PROJECT}" "${POSTGRES_SERVICE}" "${PGUSER}"
if ! golden_path_schema_compatible "${POSTGRES_SERVICE}" "${PGUSER}" "${DB_NAME}"; then
    log "DB ${DB_NAME} still not ready ($(golden_path_schema_status_line "${POSTGRES_SERVICE}" "${PGUSER}" "${DB_NAME}")); wiping postgres volume and retrying..."
    golden_path_remediate_database "${PROJECT}" "${DB_NAME}" "${POSTGRES_SERVICE}" "${PGUSER}" 1
    POSTGRES_SERVICE="$(golden_path_postgres_service "${PROJECT}" "${REPO_ROOT}")"
    golden_path_ensure_postgres_up "${PROJECT}" "${POSTGRES_SERVICE}" "${PGUSER}"
fi
if ! golden_path_schema_compatible "${POSTGRES_SERVICE}" "${PGUSER}" "${DB_NAME}"; then
    golden_path_emit_schema_failure "${PROJECT}" "${DB_NAME}" "${POSTGRES_SERVICE}" "${PGUSER}"
    exit 1
fi

log "DB ${DB_NAME} ready ($(golden_path_schema_status_line "${POSTGRES_SERVICE}" "${PGUSER}" "${DB_NAME}"))."
