#!/usr/bin/env bash
# Refresh long-lived ODPM_GOLDEN_PATH_PROJECT before golden-path CI (release-packages).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=golden_path_project_lib.sh
source "${SCRIPT_DIR}/golden_path_project_lib.sh"

PROJECT="${ODPM_GOLDEN_PATH_PROJECT:?Set ODPM_GOLDEN_PATH_PROJECT}"
AUTO_REMEDIATE="${ODPM_GOLDEN_PATH_AUTO_REMEDIATE:-1}"

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

REPO_ROOT="$(golden_path_repo_root)"
POSTGRES_SERVICE="$(golden_path_postgres_service "${PROJECT}" "${REPO_ROOT}")"
PGUSER="$(golden_path_read_env "${PROJECT}" POSTGRES_ODOO_USER odoo)"
PGPASSWORD="$(golden_path_read_env "${PROJECT}" POSTGRES_ODOO_PASS odoo)"
export PGPASSWORD
DB_NAME="$(golden_path_read_env "${PROJECT}" ODOO_DB_NAME test_db)"

cd "${PROJECT}"
docker compose down --remove-orphans 2>/dev/null || true

odpm --skip-start --no-git-update
echo "Golden-path project refreshed with $(odpm --version 2>&1 | head -1)"

if [[ "${AUTO_REMEDIATE}" == "0" || "${AUTO_REMEDIATE}" == "false" ]]; then
    echo "ODPM_GOLDEN_PATH_AUTO_REMEDIATE=${AUTO_REMEDIATE}; skipping DB schema check."
    exit 0
fi

golden_path_ensure_postgres_up "${PROJECT}" "${POSTGRES_SERVICE}" "${PGUSER}"
trap 'cd "${PROJECT}" && docker compose down --remove-orphans 2>/dev/null || true' EXIT

HAD_DATABASE=0
if golden_path_database_exists "${POSTGRES_SERVICE}" "${PGUSER}" "${DB_NAME}"; then
    HAD_DATABASE=1
    TRANSLATE_TYPE="$(golden_path_translate_column_type "${POSTGRES_SERVICE}" "${PGUSER}" "${DB_NAME}")"
    if golden_path_schema_compatible "${TRANSLATE_TYPE}"; then
        echo "Golden-path DB ${DB_NAME} schema OK (translate=boolean)."
        exit 0
    fi
    echo "Golden-path DB ${DB_NAME} schema stale (translate=${TRANSLATE_TYPE:-missing}); remediating..."
else
    echo "Golden-path DB ${DB_NAME} missing; initializing..."
fi

golden_path_remediate_database "${PROJECT}" "${DB_NAME}" "${HAD_DATABASE}"

golden_path_ensure_postgres_up "${PROJECT}" "${POSTGRES_SERVICE}" "${PGUSER}"
TRANSLATE_TYPE="$(golden_path_translate_column_type "${POSTGRES_SERVICE}" "${PGUSER}" "${DB_NAME}")"
if ! golden_path_schema_compatible "${TRANSLATE_TYPE}"; then
    echo "::error::Golden-path DB ${DB_NAME} still incompatible after remediation (translate=${TRANSLATE_TYPE:-missing})." >&2
    exit 1
fi

echo "Golden-path DB ${DB_NAME} reinitialized for Odoo 19+ (translate=boolean)."
