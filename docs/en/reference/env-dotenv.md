# `.env` file variables

> **AI-translated** from Russian.

Environment parameters (ports, scenario, backup paths, git clone roots) live in **`.env`**. Since **4.7**, odpm **merges** two files on read ([hierarchy](config-hierarchy.md), [ADR-013](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-013-layered-env-dotenv.md)):

| File | Role |
|------|------|
| `~/.odpm/.env` | Shared user profile (base) |
| `.env` in the project directory | Overrides for **this** environment (overlay, stronger than home) |

The first-run wizard **writes** to project `.env` when that file already exists, else to `~/.odpm/.env`. In project `.env` you can keep only differing keys (e.g. `ODOO_PORT`, `ODPM_COMPOSE_PREFIX`) while `BACKUP_DIR` and `ODOO_PROJECTS_DIR` stay in home.

On the **first interactive** run, the setup wizard asks questions. Press Enter for unfamiliar items.

### Example: shared home, per-project overrides

`~/.odpm/.env`:

```ini
BACKUP_DIR=/home/dev/backups
ODOO_PROJECTS_DIR=/home/dev/odoo_projects
PATH_TO_SSH_KEY=/home/dev/.ssh/id_ed25519
ODPM_LOCALE=en_US
```

`<project>/.env`:

```ini
ODOO_PORT=8070
ODPM_COMPOSE_PREFIX=acme
ODOO_PLATFORM_DIR=/work/client/odoo/19.0
```

## Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `BACKUP_DIR` | Database archive directory (`--db-backup`, `--db-restore`) | `~/odoo_backups` |
| `ODOO_PROJECTS_DIR` | Where to clone platform and git dependencies | `~/odoo_projects` |
| `ODOO_PORT` | Odoo HTTP port on the host | `8069` |
| `POSTGRES_PORT` | PostgreSQL port on the host (in `server` scenario — localhost only) | `5432` |
| `POSTGRES_SERVICE_NAME` | PostgreSQL service name in `docker-compose.yml` and `db_host` in `odoo.conf` (when `ODPM_COMPOSE_PREFIX` is unset) | `db` |
| `ODPM_COMPOSE_PREFIX` | Prefix for **full** compose-stack isolation: `db`/`odoo` service keys, `postgres-data` volume, Docker Compose project name | unset |
| `ODPM_COMPOSE_NETWORK` | Logical name of **one** compose network for the whole stack (managed bridge or external); unset — implicit default network | unset |
| `ODPM_COMPOSE_NETWORK_EXTERNAL` | `1` / `true` — network already exists on the host (`external: true`); name not prefixed | `0` |
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

See [ADR-012](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-012-compose-service-prefix.md), [PostgreSQL state](database-state.md).

## `ODPM_COMPOSE_NETWORK` / `ODPM_COMPOSE_NETWORK_EXTERNAL`

Optionally declare **one** named Docker Compose network for the **entire** odpm stack (`db`, `odoo`, sidecars). When unset, odpm does **not** add a `networks:` section to `docker-compose.yml` — services stay on the project's implicit default network (same as 4.6).

| Mode | `.env` | Behaviour |
|------|--------|-----------|
| **Default** | variables unset | No `networks:` in YAML |
| **Managed** | `ODPM_COMPOSE_NETWORK=stack` | `networks: { stack: { driver: bridge } }`; services without their own `networks` are attached |
| **External** | `ODPM_COMPOSE_NETWORK=proxy` + `ODPM_COMPOSE_NETWORK_EXTERNAL=1` | `external: true`; name **without** prefix (shared reverse-proxy network) |

With **`ODPM_COMPOSE_PREFIX=acme`**, managed network `stack` becomes physical **`acme-stack`**; external `proxy` stays `proxy`.

Name normalization matches prefix (`[a-z0-9-]`, start with a letter). Invalid values disable the network (warning). `ODPM_COMPOSE_NETWORK_EXTERNAL` without a network name has no effect.

Typical split ([ADR-013](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-013-layered-env-dotenv.md)):

`~/.odpm/.env`:

```ini
ODPM_COMPOSE_NETWORK=proxy
ODPM_COMPOSE_NETWORK_EXTERNAL=1
```

`<project>/.env`:

```ini
ODPM_COMPOSE_PREFIX=acme
ODPM_COMPOSE_NETWORK=stack
```

Manifest sidecars with `networks: ["stack"]` are consistent only when `ODPM_COMPOSE_NETWORK=stack`; otherwise `odpm manifest validate` logs a warning. See [plugins](plugins.md), [ADR-014](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-014-compose-stack-network.md).

Changing the network does **not** cause database drift (not in `last_run.json`); `docker-compose.yml` is regenerated on the next materialize.

## Variables for manifest substitution

Besides built-in odpm keys, `.env` may define **arbitrary** names for `${VAR}` in `odpm.json` and `user_settings.json` (e.g. `ODOO_PLATFORM_DIR`, `OCA_WEB_PATH`, `GIT_HOST`). They **do not** control ports or scenario by themselves — they are only substituted into whitelist manifest fields when JSON is read.

Priority for `${VAR}`: odpm **process** variables override the effective merged `.env` (home + project). Empty default in manifest: `${VAR:-}`.

Typical project `.env` fragment for local development:

```ini
ODOO_PLATFORM_DIR=/home/dev/odoo/19.0
DEVELOPING_PROJECT_DIR=/home/dev/my_addons
OCA_WEB_PATH=/home/dev/src/oca/web
GIT_HOST=git.company.example
```

See [odpm.json](odpm-json.md), [user_settings.json](user-settings.md), [configuration hierarchy](config-hierarchy.md).
