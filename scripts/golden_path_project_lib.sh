#!/usr/bin/env bash
# Shared helpers for golden-path runner maintenance scripts.
set -euo pipefail

golden_path_repo_root() {
    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[1]:-${BASH_SOURCE[0]}}")" && pwd)"
    cd "${script_dir}/.." && pwd
}

golden_path_read_env() {
    local project="$1"
    local key="$2"
    local default="$3"
    if [[ -f "${project}/.env" ]]; then
        local line
        line="$(grep -E "^${key}=" "${project}/.env" | tail -1 || true)"
        if [[ -n "${line}" ]]; then
            echo "${line#*=}"
            return
        fi
    fi
    echo "${default}"
}

golden_path_postgres_service() {
    local project="$1"
    local repo_root="$2"
    python3 - <<PY
from pathlib import Path
import sys

sys.path.insert(0, "${repo_root}")
from tests.integration.compose_golden_patch import postgres_service_name_from_compose

print(
    postgres_service_name_from_compose(
        Path("${project}/docker-compose.yml").read_text(encoding="utf-8")
    )
)
PY
}

golden_path_ensure_postgres_up() {
    local project="$1"
    local postgres_service="$2"
    local pguser="$3"

    cd "${project}"
    docker compose down --remove-orphans 2>/dev/null || true
    docker compose up -d "${postgres_service}"

    local attempt
    for attempt in $(seq 1 30); do
        if docker compose exec -T "${postgres_service}" pg_isready -U "${pguser}" >/dev/null 2>&1; then
            return 0
        fi
        sleep 1
    done
    echo "Postgres did not become ready in ${project}" >&2
    return 1
}

golden_path_database_exists() {
    local postgres_service="$1"
    local pguser="$2"
    local db_name="$3"

    docker compose exec -T "${postgres_service}" psql -U "${pguser}" -d postgres -tAc \
        "SELECT 1 FROM pg_database WHERE datname = '${db_name}'" | grep -q 1
}

golden_path_translate_column_type() {
    local postgres_service="$1"
    local pguser="$2"
    local db_name="$3"

    docker compose exec -T "${postgres_service}" psql -U "${pguser}" -d "${db_name}" -tAc \
        "SELECT data_type FROM information_schema.columns \
         WHERE table_schema = 'public' AND table_name = 'ir_model_fields' AND column_name = 'translate'"
}

golden_path_schema_compatible() {
    local translate_type="$1"
    [[ "${translate_type}" == "boolean" ]]
}

golden_path_remediate_database() {
    local project="$1"
    local db_name="$2"
    local had_database="$3"

    cd "${project}"
    docker compose down --remove-orphans 2>/dev/null || true

    local drop_flag=()
    if [[ "${had_database}" == "1" ]]; then
        drop_flag=(--db-drop)
    fi

    echo "Golden-path: reinitializing Odoo database ${db_name} (had_database=${had_database})..."
    odpm -d "${db_name}" "${drop_flag[@]}" -i --odoo-bin --stop-after-init
    docker compose down --remove-orphans 2>/dev/null || true
}
