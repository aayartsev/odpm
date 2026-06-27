# `.env` file variables

> **AI-translated** from Russian.

The **`.env`** file sets parameters for **this** odpm environment directory: ports, scenario, backup paths, and git clone locations. If it lives **in the project directory**, it **fully replaces** `~/.odpm/.env` — values from the two files are not merged ([hierarchy](config-hierarchy.md)).

On the **first interactive** odpm run, the setup wizard asks questions and writes answers to `.env` (global or project-level). Press Enter for unfamiliar items.

## Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `BACKUP_DIR` | Database archive directory (`--db-backup`, `--db-restore`) | `~/odoo_backups` |
| `ODOO_PROJECTS_DIR` | Where to clone platform and git dependencies | `~/odoo_projects` |
| `ODOO_PORT` | Odoo HTTP port on the host | `8069` |
| `POSTGRES_PORT` | PostgreSQL port on the host (in `server` scenario — localhost only) | `5432` |
| `POSTGRES_SERVICE_NAME` | PostgreSQL service name in `docker-compose.yml` and `db_host` in `odoo.conf` (when `ODPM_COMPOSE_PREFIX` is unset) | `db` |
| `ODPM_COMPOSE_PREFIX` | Prefix for **full** compose-stack isolation: `db`/`odoo` service keys, `postgres-data` volume, Docker Compose project name | unset |
| `DEBUGGER_PORT` | Debugger port; see [backend semantics](#debugger_port-and-backend) | `5678` |
| `ODPM_DEBUGGER_BACKEND` | `debugpy_listen` or `pydevd_connect` | `debugpy_listen` |
| `ODPM_IDE` | Which IDE settings to generate: `vscode`, `pycharm`, `both`, `none` | `vscode` |
| `ODPM_DEBUGGER_CONNECT_HOST` | IDE host for `pydevd_connect` (where the container connects to the Debug Server) | `host.docker.internal` |
| `ODPM_DEBUGGER_SUSPEND` | `1` / `y` — Odoo waits for the IDE after `settrace` (`pydevd_connect`) | `0` |
| `GEVENT_PORT` | gevent websocket port | `8072` |
| `ODPM_SCENARIO` | `developer`, `server`, or `ci` | `developer` |
| `ODPM_LOCALE` | odpm message language, e.g. `ru_RU` | from system | see [locale.md](locale.md) |
| `PATH_TO_SSH_KEY` | SSH key path for git (rarely needed) | empty |

Changing `POSTGRES_SERVICE_NAME`, `POSTGRES_PORT`, or `ODPM_COMPOSE_PREFIX` relative to the saved snapshot causes **database drift** — see [PostgreSQL state](database-state.md).

## `DEBUGGER_PORT` and backend

| `ODPM_DEBUGGER_BACKEND` | What `DEBUGGER_PORT` means | Compose |
|-------------------------|----------------------------|---------|
| **`debugpy_listen`** | Port **in the container**, published to the host (`5678:5678`) | IDE connects to `localhost:DEBUGGER_PORT` |
| **`pydevd_connect`** | **Debug Server port on the host** (PyCharm listens) | Port **not** published; `extra_hosts` for `host.docker.internal` on Linux |

Detailed workflow: [IDE debugging](../operations/vscode-debug.md).

Fields `ODPM_DEBUGGER_CONNECT_HOST` and `ODPM_DEBUGGER_SUSPEND` always land in `.odpm/runtime/config.json`; for `debugpy_listen` the runtime does not use them.

## Examples

### VS Code / Cursor (default)

```ini
DEBUGGER_PORT=5678
ODPM_DEBUGGER_BACKEND=debugpy_listen
ODPM_IDE=vscode
```

### PyCharm Debug Server

```ini
DEBUGGER_PORT=5678
ODPM_DEBUGGER_BACKEND=pydevd_connect
ODPM_IDE=pycharm
ODPM_DEBUGGER_CONNECT_HOST=host.docker.internal
ODPM_DEBUGGER_SUSPEND=1
```

### Full `.env` fragment

```ini
BACKUP_DIR=/home/user/odoo_backups
ODOO_PROJECTS_DIR=/home/user/odoo_projects
PATH_TO_SSH_KEY=
ODOO_PORT=8069
POSTGRES_PORT=5432
POSTGRES_SERVICE_NAME=db
DEBUGGER_PORT=5678
ODPM_DEBUGGER_BACKEND=debugpy_listen
ODPM_IDE=vscode
GEVENT_PORT=8072
ODPM_SCENARIO=developer
ODPM_LOCALE=ru_RU
```

## SSH and git

The setup wizard **does not ask** for an SSH key path. OpenSSH configuration (`~/.ssh/config`, ssh-agent) is usually enough.

The **`PATH_TO_SSH_KEY`** variable is needed when git cannot use standard SSH (typical on an isolated build machine):

```ini
PATH_TO_SSH_KEY=/home/user/.ssh/id_ed25519
```

One key applies to all specified remote repositories.

## `POSTGRES_SERVICE_NAME`

PostgreSQL service name in `docker-compose.yml` and `db_host` value in `odoo.conf` (DNS inside the docker network). Lowercase letters, digits, `_`, and `-` are allowed; the name must start with a letter. After a change, regenerate `docker-compose.yml` and `odoo.conf` (a normal `odpm` run).

**Ignored** when **`ODPM_COMPOSE_PREFIX`** is set — postgres is named `{prefix}db` (e.g. `acme-db`), with a warning in the log.

## `ODPM_COMPOSE_PREFIX`

Optional prefix for **full compose-stack isolation** on a shared host: multiple odpm environments without colliding service names, volumes, or Docker Compose project scope.

| Mode | Behaviour |
|------|-----------|
| **Unset** | Same as 4.6: postgres from `POSTGRES_SERVICE_NAME` (default `db`), odoo `odoo`, volume `postgres-data` |
| **Set** (`acme` or `acme-`) | Services `acme-db`, `acme-odoo`; volume `acme-postgres-data`; project name / `docker compose -p` — `acme` |

Normalization: lowercase, charset `[a-z0-9-]`, must start with a letter; trailing `-` in `.env` is optional. Invalid values are **ignored** (prefix disabled, warning logged).

Manifest sidecars keep **logical** names (`depends_on: ["db"]`); odpm rewrites them to physical names when generating `docker-compose.yml`.

Example:

```ini
ODPM_COMPOSE_PREFIX=acme
```

See [ADR-012](../../contributing/adr-012-compose-service-prefix.md), [PostgreSQL state](database-state.md).

## Variables for manifest substitution

Besides built-in odpm keys, `.env` may define **arbitrary** names for `${VAR}` in `odpm.json` and `user_settings.json` (e.g. `ODOO_PLATFORM_DIR`, `OCA_WEB_PATH`, `GIT_HOST`). They **do not** control ports or scenario by themselves — they are only substituted into whitelist manifest fields when JSON is read.

Priority for `${VAR}`: odpm **process** variables override the project `.env`. Empty default in manifest: `${VAR:-}`.

Typical project `.env` fragment for local development:

```ini
ODOO_PLATFORM_DIR=/home/dev/odoo/19.0
DEVELOPING_PROJECT_DIR=/home/dev/my_addons
OCA_WEB_PATH=/home/dev/src/oca/web
GIT_HOST=git.company.example
```

See [odpm.json](odpm-json.md), [user_settings.json](user-settings.md), [configuration hierarchy](config-hierarchy.md).
