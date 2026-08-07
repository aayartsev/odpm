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

golden_path_db_has_odoo_tables() {
    local postgres_service="$1"
    local pguser="$2"
    local db_name="$3"

    docker compose exec -T "${postgres_service}" psql -U "${pguser}" -d "${db_name}" -tAc \
        "SELECT 1 FROM information_schema.tables \
         WHERE table_schema = 'public' AND table_name = 'ir_module_module' LIMIT 1" | grep -q 1
}

golden_path_base_module_version() {
    local postgres_service="$1"
    local pguser="$2"
    local db_name="$3"

    docker compose exec -T "${postgres_service}" psql -U "${pguser}" -d "${db_name}" -tAc \
        "SELECT latest_version FROM ir_module_module \
         WHERE name = 'base' AND state = 'installed' LIMIT 1" | tr -d '[:space:]'
}

golden_path_module_is_installed() {
    local postgres_service="$1"
    local pguser="$2"
    local db_name="$3"
    local module_name="$4"

    docker compose exec -T "${postgres_service}" psql -U "${pguser}" -d "${db_name}" -tAc \
        "SELECT 1 FROM ir_module_module \
         WHERE name = '${module_name}' AND state = 'installed' LIMIT 1" | grep -q 1
}

golden_path_column_exists() {
    local postgres_service="$1"
    local pguser="$2"
    local db_name="$3"
    local table_name="$4"
    local column_name="$5"

    docker compose exec -T "${postgres_service}" psql -U "${pguser}" -d "${db_name}" -tAc \
        "SELECT 1 FROM information_schema.columns \
         WHERE table_schema = 'public' \
           AND table_name = '${table_name}' \
           AND column_name = '${column_name}' \
         LIMIT 1" | grep -q 1
}

golden_path_platform_dir() {
    local project="${1:-}"
    local from_env=""

    if [[ -n "${project}" ]]; then
        from_env="$(golden_path_read_env "${project}" ODOO_PLATFORM_DIR "")"
        if [[ -n "${from_env}" && -d "${from_env}" ]]; then
            echo "${from_env}"
            return 0
        fi
    fi
    if [[ -n "${ODOO_PLATFORM_DIR:-}" && -d "${ODOO_PLATFORM_DIR}" ]]; then
        echo "${ODOO_PLATFORM_DIR}"
        return 0
    fi
    return 1
}

# True when mounted Odoo source still defines res.lang.short_time_format
# (pre datetime-remake 19.0). Unknown/missing source → false (skip column gate).
golden_path_code_expects_short_time_format() {
    local project="${1:-}"
    local platform_dir res_lang

    platform_dir="$(golden_path_platform_dir "${project}" 2>/dev/null || true)"
    [[ -n "${platform_dir}" ]] || return 1
    res_lang="${platform_dir}/odoo/addons/base/models/res_lang.py"
    [[ -f "${res_lang}" ]] || return 1
    grep -Eq '(^|[[:space:]])short_time_format[[:space:]]*=' "${res_lang}"
}

golden_path_schema_status_line() {
    local postgres_service="$1"
    local pguser="$2"
    local db_name="$3"
    local base_version web_state short_time

    if ! golden_path_db_has_odoo_tables "${postgres_service}" "${pguser}" "${db_name}"; then
        echo "odoo_tables=missing base=missing web=missing"
        return
    fi
    base_version="$(golden_path_base_module_version "${postgres_service}" "${pguser}" "${db_name}")"
    if golden_path_module_is_installed "${postgres_service}" "${pguser}" "${db_name}" web; then
        web_state=installed
    else
        web_state=missing
    fi
    if golden_path_column_exists "${postgres_service}" "${pguser}" "${db_name}" \
        res_lang short_time_format; then
        short_time=present
    else
        short_time=absent
    fi
    echo "base=${base_version:-missing} web=${web_state} short_time_format=${short_time}"
}

# Odoo 19 golden-path: base 19.x installed + web installed.
# Do not require res_lang.short_time_format by default — removed in Odoo 19 datetime remake.
# When mounted Odoo source still defines the field, require the column (code/DB sync).
# Do not use ir_model_fields.translate SQL type — on Odoo 19 it stays character varying.
golden_path_schema_compatible() {
    local postgres_service="$1"
    local pguser="$2"
    local db_name="$3"
    local project="${4:-${ODPM_GOLDEN_PATH_PROJECT:-}}"
    local base_version

    if ! golden_path_db_has_odoo_tables "${postgres_service}" "${pguser}" "${db_name}"; then
        return 1
    fi
    base_version="$(golden_path_base_module_version "${postgres_service}" "${pguser}" "${db_name}")"
    [[ -n "${base_version}" && "${base_version}" == 19* ]] || return 1
    golden_path_module_is_installed "${postgres_service}" "${pguser}" "${db_name}" web || return 1
    if golden_path_code_expects_short_time_format "${project}"; then
        golden_path_column_exists "${postgres_service}" "${pguser}" "${db_name}" \
            res_lang short_time_format || return 1
    fi
    return 0
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
    local postgres_service="$3"
    local pguser="$4"
    local status_line init_modules odoo_version base_version

    status_line="$(golden_path_schema_status_line "${postgres_service}" "${pguser}" "${db_name}")"
    init_modules="$(golden_path_init_modules)"
    odoo_version="$(golden_path_odoo_version_from_manifest "${project}" || true)"
    base_version="${status_line#*base=}"
    base_version="${base_version%% web=*}"

    echo "::error::Golden-path DB ${db_name} not ready for Odoo 19 golden-path (${status_line})." >&2
    if [[ -n "${base_version}" && "${base_version}" != missing && "${base_version}" != 19* ]]; then
        echo "Installed base module is ${base_version}; expected 19.x (stale DB from older Odoo major)." >&2
    elif [[ "${status_line}" == *"web=missing"* ]]; then
        echo "Module web is not installed; golden-path needs /web." >&2
        echo "Run: odpm -d ${db_name} --odoo-bin -i ${init_modules} --stop-after-init" >&2
    elif [[ "${status_line}" == *"odoo_tables=missing"* ]]; then
        echo "Database exists but has no Odoo tables; run init on the runner." >&2
    elif [[ "${status_line}" == *"short_time_format=absent"* ]] \
        && golden_path_code_expects_short_time_format "${project}"; then
        echo "Mounted Odoo still defines res.lang.short_time_format but the column is missing." >&2
        echo "Prefer: git pull Odoo 19.0 past the datetime remake; or remedi ate DB to match mounted source." >&2
        echo "Run: ODPM_GOLDEN_PATH_AUTO_REMEDIATE=1 bash scripts/refresh_golden_path_project.sh" >&2
    fi
    if [[ -n "${odoo_version}" && "${odoo_version}" != 19* ]]; then
        echo "odpm.json reports odoo_version=${odoo_version}; golden-path expects 19.0." >&2
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
