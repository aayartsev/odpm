#!/usr/bin/env bash
# Fail fast when golden-path Postgres schema is incompatible with Odoo 19+.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"
PROJECT="${ODPM_GOLDEN_PATH_PROJECT:?Set ODPM_GOLDEN_PATH_PROJECT}"

if [[ ! -d "${PROJECT}" ]]; then
    echo "ODPM_GOLDEN_PATH_PROJECT is not a directory: ${PROJECT}" >&2
    exit 1
fi

cd "${PROJECT}"

POSTGRES_SERVICE="$(
    python3 - <<PY
from pathlib import Path
import sys

sys.path.insert(0, "${REPO_ROOT}")
from tests.integration.compose_golden_patch import postgres_service_name_from_compose

print(
    postgres_service_name_from_compose(
        Path("${PROJECT}/docker-compose.yml").read_text(encoding="utf-8")
    )
)
PY
)"

read_env() {
    local key="$1"
    local default="$2"
    if [[ -f .env ]]; then
        local line
        line="$(grep -E "^${key}=" .env | tail -1 || true)"
        if [[ -n "${line}" ]]; then
            echo "${line#*=}"
            return
        fi
    fi
    echo "${default}"
}

PGUSER="$(read_env POSTGRES_ODOO_USER odoo)"
PGPASSWORD="$(read_env POSTGRES_ODOO_PASS odoo)"
export PGPASSWORD

docker compose down --remove-orphans 2>/dev/null || true
docker compose up -d "${POSTGRES_SERVICE}"
trap 'docker compose down --remove-orphans 2>/dev/null || true' EXIT

for _ in $(seq 1 30); do
    if docker compose exec -T "${POSTGRES_SERVICE}" pg_isready -U "${PGUSER}" >/dev/null 2>&1; then
        break
    fi
    sleep 1
done

DB_NAME="$(read_env ODOO_DB_NAME test_db)"
if ! docker compose exec -T "${POSTGRES_SERVICE}" psql -U "${PGUSER}" -d postgres -tAc \
    "SELECT 1 FROM pg_database WHERE datname = '${DB_NAME}'" | grep -q 1; then
    echo "Preflight: database ${DB_NAME} does not exist yet (first init required on runner)." >&2
    echo "Run: cd ${PROJECT} && odpm -d ${DB_NAME} -i base,web" >&2
    exit 1
fi

TRANSLATE_TYPE="$(
    docker compose exec -T "${POSTGRES_SERVICE}" psql -U "${PGUSER}" -d "${DB_NAME}" -tAc \
        "SELECT data_type FROM information_schema.columns \
         WHERE table_schema = 'public' AND table_name = 'ir_model_fields' AND column_name = 'translate'"
)"

if [[ "${TRANSLATE_TYPE}" != "boolean" ]]; then
    echo "::error::Golden-path Postgres schema is stale for Odoo 19 (ir_model_fields.translate=${TRANSLATE_TYPE:-missing})." >&2
    echo "Recreate the database on the self-hosted runner (backup, drop ${DB_NAME} or postgres volume, then odpm -d ${DB_NAME} -i base,web)." >&2
    echo "See docs/contributing/ci.md (golden-path maintenance table)." >&2
    exit 1
fi

echo "Preflight OK: ${DB_NAME} schema compatible with Odoo 19+ (translate=boolean)."
