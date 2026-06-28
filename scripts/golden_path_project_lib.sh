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

golden_path_init_modules() {
    echo "${ODPM_GOLDEN_PATH_INIT_MODULES:-base,web}"
}

golden_path_sql_drop_database() {
    local postgres_service="$1"
    local pguser="$2"
    local db_name="$3"

    if ! golden_path_database_exists "${postgres_service}" "${pguser}" "${db_name}"; then
        return 0
    fi

    echo "Golden-path: dropping database ${db_name} via PostgreSQL..."
    docker compose exec -T "${postgres_service}" psql -U "${pguser}" -d postgres -v ON_ERROR_STOP=1 <<-SQL
SELECT pg_terminate_backend(pid)
FROM pg_stat_activity
WHERE datname = '${db_name}' AND pid <> pg_backend_pid();
DROP DATABASE IF EXISTS "${db_name}";
SQL
}

golden_path_postgres_data_dir() {
    local project="$1"
    echo "${project}/data/postgresql/var/lib/postgresql/data"
}

golden_path_odoo_version_from_manifest() {
    local project="$1"
    python3 - "${project}" <<'PY'
import json
import sys
from pathlib import Path

root = Path(sys.argv[1])
for rel in ("odpm.json", "developing/odpm.json"):
    path = root / rel
    if not path.is_file():
        continue
    try:
        version = json.loads(path.read_text(encoding="utf-8")).get("odoo_version")
    except (OSError, json.JSONDecodeError):
        continue
    if version:
        print(version)
        break
PY
}

golden_path_emit_schema_failure() {
    local project="$1"
    local db_name="$2"
    local translate_type="$3"
    local init_modules odoo_version

    init_modules="$(golden_path_init_modules)"
    odoo_version="$(golden_path_odoo_version_from_manifest "${project}" || true)"

    echo "::error::Golden-path DB ${db_name} incompatible with Odoo 19+ (ir_model_fields.translate=${translate_type:-missing})." >&2
    if [[ -n "${odoo_version}" && "${odoo_version}" != 19* && "${odoo_version}" != "19.0" ]]; then
        echo "odpm.json reports odoo_version=${odoo_version}; golden-path preflight expects Odoo 19 (translate=boolean)." >&2
        echo "Update the Odoo platform checkout on the runner, then re-run refresh." >&2
    elif [[ "${translate_type}" == "character varying" ]]; then
        echo "translate=character varying usually means Odoo < 19 or base modules were not installed." >&2
        echo "Ensure init runs: odpm -d ${db_name} --odoo-bin -i ${init_modules} --stop-after-init" >&2
    fi
    echo "Manual wipe (postgres data is often root-owned from Docker):" >&2
    echo "  cd ${project} && docker compose down" >&2
    echo "  docker run --rm -v \"$(golden_path_postgres_data_dir "${project}"):/data\" alpine sh -c 'find /data -mindepth 1 -maxdepth 1 -exec rm -rf {} +'" >&2
    echo "See docs/contributing/ci.md (golden-path maintenance table)." >&2
}

golden_path_wipe_postgres_data() {
    local project="$1"
    local data_dir
    data_dir="$(golden_path_postgres_data_dir "${project}")"
    if [[ ! -d "${data_dir}" ]]; then
        return 0
    fi
    echo "Golden-path: wiping postgres data at ${data_dir}..."
    if docker run --rm -v "${data_dir}:/data:rw" alpine:3.20 \
        sh -c 'find /data -mindepth 1 -maxdepth 1 -exec rm -rf {} +'; then
        return 0
    fi
    if command -v sudo >/dev/null 2>&1 \
        && sudo find "${data_dir}" -mindepth 1 -maxdepth 1 -exec rm -rf {} +; then
        return 0
    fi
    echo "::error::Cannot wipe postgres data at ${data_dir} (permission denied)." >&2
    echo "On the self-hosted runner:" >&2
    echo "  docker run --rm -v \"${data_dir}:/data\" alpine sh -c 'find /data -mindepth 1 -maxdepth 1 -exec rm -rf {} +'" >&2
    return 1
}

golden_path_remediate_database() {
    local project="$1"
    local db_name="$2"
    local postgres_service="$3"
    local pguser="$4"
    local wipe_volume="${5:-0}"
    local init_modules
    init_modules="$(golden_path_init_modules)"

    cd "${project}"
    docker compose down --remove-orphans 2>/dev/null || true

    if [[ "${wipe_volume}" == "1" ]]; then
        golden_path_wipe_postgres_data "${project}"
    else
        golden_path_ensure_postgres_up "${project}" "${postgres_service}" "${pguser}"
        golden_path_sql_drop_database "${postgres_service}" "${pguser}" "${db_name}"
        docker compose down --remove-orphans 2>/dev/null || true
    fi

    echo "Golden-path: initializing Odoo database ${db_name} (modules=${init_modules})..."
    # Pass -i MODULES via --odoo-bin only: user_settings.init_modules may be empty and
    # odpm's -i flag would not forward module names to odoo-bin.
    odpm -d "${db_name}" --odoo-bin -i "${init_modules}" --stop-after-init
    docker compose down --remove-orphans 2>/dev/null || true
}
