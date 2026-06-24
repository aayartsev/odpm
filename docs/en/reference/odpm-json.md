# odpm.json file fields

> **AI-translated** from Russian.

The **`odpm.json`** file is the formal **stack description** of an Odoo project: versions, repositories, dependencies. It is committed to git with the modules so any team member and the build machine get the **same composition**.

odpm 4.4 supports two formats:

| Format | Marker | When to use |
|--------|--------|-------------|
| **v1 flat** (default) | `odpm_version: "4.0"`, no `manifest_schema` | Existing projects, unchanged |
| **v2 nested** | `manifest_schema: 2`, `requires_odpm: "4.6.0"` | `services`, `hooks`, `locks` in the manifest |

Migration: **`odpm manifest migrate`** — see [manifest-migration.md](manifest-migration.md).

## Flat v1 (top-level fields)

| Field | Purpose |
|-------|---------|
| `python_version` | Python version in the container, e.g. `"3.10"` |
| `distro_name` | Linux family (currently `"debian"` is supported) |
| `distro_version` | Distribution version: `"11"`, `"12"`, `"bullseye"` |
| `postgres_version` | PostgreSQL version in compose, e.g. `"15"` |
| `odoo_version` | Odoo version: `"19.0"`, `"18.0"` |
| `dependencies` | List of git links to addon repositories |
| `requirements_txt` | List of strings as in requirements.txt |
| `odoo_git_link` | **Platform** repository; branch/commit after a space |
| `platform_name` | Fork Python package name (default `"odoo"`) |
| `odoo_build_date` | Nightly build date `YYYYMMDD` or `"latest"` |
| `odpm_version` | **v1 format contract string** (`"4.0"`), not the manager version |

## Version axes (manager vs manifest)

The **product** has one version; the **manifest** uses separate format fields:

| Constant / field | Example | Purpose |
|------------------|---------|---------|
| `RELEASE_VERSION` / `ODPM_VERSION` | `"4.6.0"` | **Installed manager** version (`odpm --version`, pip, deb/rpm) |
| `MANIFEST_V1_CONTRACT_LINE` | `"4.0"` | `odpm_version` string odpm **writes to new** flat projects |
| `DEFAULT_ODPM_VERSION` | `"3.0"` | **Legacy fallback** when `odpm_version` is **missing** in flat v1 (manager logs a deprecation warning; behaviour unchanged) |

Compat behaviour (`dev_project/manifest/compat.py`):

- Flat v1 **without** `manifest_schema` and **without** `odpm_version` → contract is treated as `"3.0"` (supported by manager 4.6.0); odpm logs a **warning** suggesting `odpm_version: "4.0"`.
- New projects and migrations → `odpm_version: "4.0"`.
- v2 nested → `requires_odpm` (minimum manager semver; new projects get current `RELEASE_VERSION`), not `odpm_version`.

Validation without bootstrap: **`odpm manifest validate`** (JSON Schema v1 or v2 + compat-check).

## Nested v2 (additional blocks)

Required v2 fields: `manifest_schema`, `requires_odpm`, `platform`, `python`, `distro`, `postgres`.

| Block / field | Purpose |
|---------------|---------|
| `manifest_schema` | `2` |
| `requires_odpm` | Minimum odpm version, e.g. `"4.6.0"` |
| `platform.git` | Analog of `odoo_git_link` |
| `platform.build_date` | Analog of `odoo_build_date` |
| `python` | Analog of `python_version` |
| `distro.name` / `distro.version` | Analog of `distro_name` / `distro_version` |
| `postgres` | Analog of `postgres_version` |
| `requirements` | Analog of `requirements_txt` |
| `developing.git` | Developing project URI |
| `locks.git` | Declarative git SHAs (sync with `.odpm/deps.lock.json`) |
| `locks.venv` | venv lock hash (optional) |
| `hooks.post_prepare` | Shell argv or plugin id after prepare |
| `hooks.pre_up` | Shell argv or plugin id before `docker compose up` |
| `services.<name>` | Extra compose services: `image` required; optional `ports[]`, `environment`, `volumes[]`, `depends_on[]`, `restart`, `user`, `tty`, `command[]`, `entrypoint[]` |

Mailpit example: [plugins.md](plugins.md).

Validation: **`odpm manifest validate`** (JSON Schema v1/v2 on host, read-only). On bootstrap, v1 passes compat-check without jsonschema; v2 uses jsonschema in `load_manifest`.

## `database` block (language and country for a new database)

Optional object for **team-wide** project identity on first database creation (`-d`):

| Field | Purpose |
|-------|---------|
| `database.language` | Odoo database language, e.g. `ru_RU`, `en_US` |
| `database.country` | Country code (`RU`, `US`) or `false` / `null` |

Manifest values **override** same-named fields in `user_settings.json` → `db_creation_data`. Local database creation parameters (`create_demo`, admin login/password) remain in [user_settings.json](user-settings.md).

Example (v1 flat or v2):

```json
"database": {
  "language": "ru_RU",
  "country": "RU"
}
```

## `odoo_conf` block (Odoo option overrides)

Optional object for **team-wide** Odoo settings in git (preview, staging, production). Manifest values **override** same-named keys in the on-disk `odoo.conf` when building `odoo_config_data` for the container; manifest is **not** written back to `odoo.conf`.

```json
"odoo_conf": {
  "options": {
    "proxy_mode": "True",
    "dbfilter": "^${PREVIEW_HOSTNAME}$",
    "workers": "2",
    "log_level": "debug"
  }
}
```

`odpm manifest validate` rejects keys managed by odpm: `addons_path`, `data_dir`, `db_host`, `db_port`, `db_user`, `db_password`, `admin_passwd`, `http_port`. See [odoo.conf](odoo-conf.md).

## Migration v1 → v2

Command **`odpm manifest migrate`** shows a unified diff of flat manifest → nested v2. With **`--write`** it writes the result to the developing project’s `odpm.json`. Details: [manifest-migration.md](manifest-migration.md).

On migration odpm moves:

| Source | v2 destination |
|--------|----------------|
| flat fields (`python_version`, `odoo_git_link`, …) | `python`, `platform`, `distro`, … |
| `database` in manifest or `db_creation_data` in `user_settings.json` | `database` |
| `developing_project` in `user_settings.json` | `developing.git` |
| `.odpm/deps.lock.json` | `locks.git` |

After migration, v1 flat is still read by manager 4.4 until the file is switched. Projects without migration are not broken.

## `${VAR}` substitution in string fields

In **whitelist fields** odpm expands environment variable references right after reading JSON:

| Field | Substitution |
|-------|--------------|
| `odoo_git_link` | yes |
| `dependencies` | yes (each list element) |
| `services.*` / `service_patches.*` (v2) | yes — `image`, `user`, `restart`, lists (`ports`, `volumes`, `command`, …), `environment` values |
| `odoo_conf.*` (v1/v2) | yes — all string values in `odoo_conf.options` |
| `hooks.*` argv (v2) | yes — at hook **execution** (not during `odpm manifest validate`) |

Syntax: **`${NAME}`** and **`${NAME:-default}`** (as in Docker Compose). Literal `$` — **`$$`**.

Value source (strongest to weakest): **process** variables (`export`, CI secrets) → keys from **project `.env`** → default in the manifest string. No separate enable flag is needed.

Example for a team manifest in git and local paths on a developer machine:

```json
{
  "odoo_git_link": "file://${ODOO_PLATFORM_DIR}",
  "dependencies": [
    "file://${OCA_WEB_PATH}",
    "https://${GIT_HOST}/company/extra.git 19.0"
  ]
}
```

In the project `.env` (or `export` / CI):

```ini
ODOO_PLATFORM_DIR=/home/dev/odoo/19.0
OCA_WEB_PATH=/home/dev/src/oca/web
GIT_HOST=git.company.example
```

Other fields (`odoo_version`, `python_version`, `requirements_txt`, …) have **no** substitution. Nested `odpm.json` in git dependencies supports the same fields — see [configuration hierarchy](config-hierarchy.md). `.odpm/deps.lock.json` stores **expanded** URLs and paths, not `${VAR}`.

v2 sidecar with paths from `.env`:

```json
"services": {
  "armtek_test": {
    "image": "autoparts_env:emulator",
    "user": "root",
    "tty": true,
    "volumes": ["${DIGITAL_AUTOPARTS_ENV_DIR}/data:/data:Z"]
  }
}
```

See [`.env` variables](env-dotenv.md), [repository links](git-links.md).

## Verified combinations

- **Debian 11:** Python 3.7, 3.10 — Odoo 11–16.
- **Debian 12:** Python 3.10 — Odoo 16–19.
- **Debian 13:** Python 3.10, 3.12.

See [your own platform repository](../scenarios/platform-fork.md), [repository links](git-links.md).
