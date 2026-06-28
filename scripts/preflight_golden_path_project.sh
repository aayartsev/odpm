#!/usr/bin/env bash
# Fail fast when golden-path Postgres schema is incompatible with Odoo 19+.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=golden_path_project_lib.sh
source "${SCRIPT_DIR}/golden_path_project_lib.sh"

REPO_ROOT="$(golden_path_repo_root)"
PROJECT="${ODPM_GOLDEN_PATH_PROJECT:?Set ODPM_GOLDEN_PATH_PROJECT}"

if [[ ! -d "${PROJECT}" ]]; then
    echo "ODPM_GOLDEN_PATH_PROJECT is not a directory: ${PROJECT}" >&2
    exit 1
fi

POSTGRES_SERVICE="$(golden_path_postgres_service "${PROJECT}" "${REPO_ROOT}")"
PGUSER="$(golden_path_read_env "${PROJECT}" POSTGRES_ODOO_USER odoo)"
PGPASSWORD="$(golden_path_read_env "${PROJECT}" POSTGRES_ODOO_PASS odoo)"
export PGPASSWORD
DB_NAME="$(golden_path_read_env "${PROJECT}" ODOO_DB_NAME test_db)"

golden_path_ensure_postgres_up "${PROJECT}" "${POSTGRES_SERVICE}" "${PGUSER}"
trap 'cd "${PROJECT}" && docker compose down --remove-orphans 2>/dev/null || true' EXIT

if ! golden_path_database_exists "${POSTGRES_SERVICE}" "${PGUSER}" "${DB_NAME}"; then
    echo "Preflight: database ${DB_NAME} does not exist yet (first init required on runner)." >&2
    echo "Run: cd ${PROJECT} && odpm -d ${DB_NAME} --odoo-bin -i base,web --stop-after-init" >&2
    echo "Or re-run release CI (refresh auto-remediates when ODPM_GOLDEN_PATH_AUTO_REMEDIATE=1)." >&2
    exit 1
fi

TRANSLATE_TYPE="$(golden_path_translate_column_type "${POSTGRES_SERVICE}" "${PGUSER}" "${DB_NAME}")"

if ! golden_path_schema_compatible "${TRANSLATE_TYPE}"; then
    golden_path_emit_schema_failure "${PROJECT}" "${DB_NAME}" "${TRANSLATE_TYPE}"
    exit 1
fi

echo "Preflight OK: ${DB_NAME} schema compatible with Odoo 19+ (translate=boolean)."
