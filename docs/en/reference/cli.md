# Command-line parameters

> **AI-translated** from Russian.

The **`odpm`** command (or `python3 …/odpm.py`) accepts parameters that set **one-off** behaviour: initialization, database work, image build, change plan. Full list with brief English hints: `odpm --help`.

Below is a reference by group. Flag names are **as in the program** (Latin).

## Project initialization

| Parameter | Description |
|-----------|-------------|
| `--init LINK` | Make the current directory an odpm project. Link: HTTPS, `git@…`, `file:///…` |
| `--branch NAME` | With `--init`: branch of the **developing** repository |
| `--odoo-version VER` | Odoo version (e.g. `19.0`) in `odpm.json` |
| `--odoo-git-link LINK` | **Platform** repository instead of official odoo/odoo |
| `--platform-name NAME` | Fork Python package name (default `odoo`) |
| `--python-version VER` | Python version in the image |
| `--distro-name NAME` | Linux distribution name (currently `debian`) |
| `--distro-version VER` | Distribution version (`11`, `12`, …) |
| `--postgres-version VER` | PostgreSQL version in compose |
| `--requirements-txt PACKAGES` | Python packages comma-separated → written to `odpm.json` |
| `--secrets-file PATH` | Import JSON v1 into `.odpm/secrets.json` (on `--init` and any run). See [local secrets](../operations/secrets.md). |

Example:

```bash
odpm --init https://github.com/aayartsev/odoo_demo_project.git --branch 19.0 \
  --odoo-version 19.0 --python-version 3.12 --distro-version 12
```

Import secrets on deploy:

```bash
odpm --init file:///path/to/my_addons \
  --secrets-file /secure/client-secrets.json

# key rotation on an existing project
odpm --secrets-file ~/new-secrets.json --skip-start
```

## Environment prepare and image

| Parameter | Description |
|-----------|-------------|
| `--skip-start` | Regenerate Docker files and compose **without** starting containers; with a lock — select revisions from the lock file |
| `--update-lock` | Write `.odpm/deps.lock.json` and exit |
| `--no-git-update` | Do not touch git; lock is **not read**; directories must already exist |
| `--build-image` | Build image for **`ci`** scenario (error otherwise) |
| `--image-tag TAG` | Docker image name and tag for `--build-image` |
| `--version` | Show odpm version |

## Change plan (dry run)

Shows which prepare steps would run **without** changing git, writing files, or `docker compose up`.

```bash
odpm plan --skip-start
odpm plan --plan-format json | jq .
odpm plan --plan-show-diff --skip-start
```

Deprecated synonym: `--plan` (prefer `plan` subcommand).

| Parameter | Description |
|-----------|-------------|
| `--plan-format {table,json}` | Table to log or JSON to stdout |
| `--plan-strict` | Exit code 1 if a required step would change |
| `--plan-show-diff` | Show differences in runtime config, compose, dockerignore |
| `--plan-no-docker` | Do not query Docker for container state |

Among prepare steps there is **`database.drift`** — comparison of PostgreSQL configuration to the `last_run.json` snapshot. See [PostgreSQL state](database-state.md).

## `database` subcommand

Inspection and recovery of the **PostgreSQL cluster** (not to be confused with Odoo databases `-d`):

```bash
odpm database status
odpm database status --format json
odpm database ensure-role
```

| Command | Description |
|---------|-------------|
| `database status` | Fingerprints, drift, postgres container and application role checks |
| `database status --format json` | Same as JSON |
| `database ensure-role` | Create or update the application role in running PostgreSQL |

Flag **`--accept-database-drift=KIND`** (repeatable) — accept drift without an interactive prompt. KIND: `data_path`, `postgres_major`, `app_role_missing`, `odpm_scenario`, `data_dir_empty_changed`.

Details: [PostgreSQL state and drift](database-state.md).

## `manifest` subcommand

Migrate `odpm.json` between schema versions:

```bash
odpm manifest migrate
odpm manifest migrate --write
odpm manifest validate
```

| Command | Description |
|---------|-------------|
| `manifest migrate` | Show unified diff of flat v1 → nested v2 transformation |
| `manifest migrate --write` | Write manifest v2 to the developing project repository |
| `manifest validate` | Validate `odpm.json` against JSON Schema (v1 flat or v2 nested) + compat-check |

Migration moves `database` (from manifest or `user_settings`), `developing.git`, and `locks.git` (from `.odpm/deps.lock.json`). See [odpm.json](odpm-json.md#migration-v1--v2).

## Database and modules

| Parameter | Description |
|-----------|-------------|
| `-d DB_NAME` | Database name; if missing — creation per `db_creation_data` |
| `-i` | Install modules from `init_modules` |
| `-u` | Update modules from `update_modules` |
| `-t`, `--test` | Run module tests; requires `-d` and usually `-i` or `-u` |
| `--screencasts` | With `-t`: save video on tour failures |
| `--odoo-bin ARGS…` | Pass arguments to the Odoo executable, e.g. `--stop-after-init` |

```bash
odpm -d test_db -i -u
odpm -d test_db -i --odoo-bin --stop-after-init
```

## Platform nightly build date

| Parameter | Description |
|-----------|-------------|
| `--odoo-build-date DATE` | `YYYYMMDD` or `YYYY-MM-DD`; overrides `odoo_build_date` in json |

## Database maintenance

| Parameter | Description |
|-----------|-------------|
| `--get-dbs-list` | List databases |
| `--db-backup [ARCHIVE]` | Backup database `-d` to `BACKUP_DIR` |
| `--db-restore ARCHIVE` | Restore archive into database `-d` |
| `--db-drop` | Drop Odoo database `-d`; with `-i`/`-u` — recreate and install modules. On a legacy cluster with another PostgreSQL owner odpm runs direct `DROP DATABASE` |

## Translations and administrator

| Parameter | Description |
|-----------|-------------|
| `--translate LANG` | Update translations (e.g. `ru_RU`) |
| `--export-po-files LANG` | Export pot/po for modules from `update_modules` |
| `--set-admin-pass` | Admin login/password from `db_default_admin_*`; requires `-d` |

## Other developer tools

| Parameter | Description |
|-----------|-------------|
| `--start-precommit` | Run pre-commit in the developing project inside the container |
| `--sql-execute` | Run SQL from `sql_queries`; requires `-d` |

## `scaffold` subcommand

Create a new module skeleton (without other odpm flags):

```bash
odpm scaffold module_name
odpm scaffold module_name -t /path/to/templates
```

| Parameter | Description |
|-----------|-------------|
| `scaffold NAME` | Generate module from Jinja2 templates |
| `-t`, `--scaffold_template_name` | Custom template directory |

Git version pinning: [deps.lock.json](deps-lock.md).
