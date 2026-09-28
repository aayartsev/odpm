# Non-interactive runs

> **AI-translated** from Russian.

If standard input is **not connected to a terminal** (no TTY), odpm **does not ask questions** via `input()`. This is how scripts, cron jobs, and many continuous integration systems work.

## Prepare in advance

**`.env` file** in the project directory or in `~/.odpm/.env`.

Alternatively, set **at least one** variable from the list in the process environment — odpm will create `~/.odpm/.env`, filling the rest with defaults:

- `BACKUP_DIR`, `ODOO_PROJECTS_DIR`
- `ODOO_PORT`, `POSTGRES_PORT`, `DEBUGGER_PORT`, `GEVENT_PORT`
- `ODPM_SCENARIO`, `ODPM_LOCALE`
- `PATH_TO_SSH_KEY` (if needed)

## Init and `odpm.json`

On `--init` without a ready `odpm.json` in the developing repository, specify **`--odoo-version`** or put `odoo_version` in the repository before running.

## Manifest with `${VAR}`

If `odpm.json` or `user_settings.json` uses `${NAME}`, set values **before** running:

| Method | Example |
|--------|---------|
| project `.env` | `ODOO_PLATFORM_DIR=/data/odoo/19.0` |
| `export` in shell / CI | `export GIT_HOST=git.corp.example` |
| default in manifest | `"file://${PATH:-/opt/odoo}"` |

The project coordinator documents required names for the team and CI — see [team coordinator role](../scenarios/team-coordinator.md). A missing variable without a default exits odpm with an error.

## Database drift in CI and scripts

Without a TTY, odpm **does not ask** about PostgreSQL configuration drift. If blocking drift is detected (`data_path`, `postgres_major`, `app_role_missing`, etc.), the run fails with an error.

Options:

1. Allow drift once from an interactive terminal (`odpm` or `odpm plan`).
2. Explicitly accept drift kind: **`--accept-database-drift=KIND`** (repeat the flag for multiple KIND values).
3. Restore the role before the stack: `odpm database ensure-role` (postgres must be running).

Example on a demo wrapper (`$ODPM_DEMO_19`): [demo-projects § S6](https://github.com/aayartsev/odpm/blob/4.4-dev/docs/contributing/demo-projects.md#s6--non-interactive-и-drift).

Example:

```bash
odpm --accept-database-drift=odpm_scenario --skip-start
odpm database ensure-role
odpm -d test_db -i -u
```

More detail: [PostgreSQL state](../reference/database-state.md).

## Docker Compose and PostgreSQL volume

On **first adoption baseline** (no `.odpm/database/last_run.json`), odpm runs `docker compose up -d -y` for the PostgreSQL service. The **`--yes`** flag prevents Compose from asking an interactive question about recreating the volume (e.g. after changing the bind-mount path from `data/postgres/...` to `data/postgresql/...`).

If you **re-initialize** an odpm 3.x directory for 4.x at the same path and init hangs on postgres, remove the old volume and run again:

```bash
docker volume rm PROJECT_NAME_postgres-data
odpm
```

The volume name matches the project directory prefix (e.g. `odoo_demo_project-19_postgres-data`). More on directory migration: [migrating from 3.0](migration-3-to-4.md).

## Example for image build scenario

```bash
export ODPM_SCENARIO=ci
export ODOO_PROJECTS_DIR=/data/odoo_projects
export BACKUP_DIR=/data/backups
odpm --init https://github.com/aayartsev/odoo_demo_project.git --branch 19.0 --skip-start
```
