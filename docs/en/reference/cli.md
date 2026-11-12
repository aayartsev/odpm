# Command-line parameters

> **AI-translated** from Russian.

The **`odpm`** command (or `python3 …/odpm.py`) accepts **subcommands** and flags for one-off behaviour: stack up, prepare files, init, image build, database ops. Full list: `odpm --help`. Version: `odpm -V` / `odpm --version`.

## Command tree

| Command | Meaning |
|---------|---------|
| `odpm up` | Prepare files and start the compose stack (incl. `-i`/`-u`, combined `--db-restore`) |
| `odpm prepare` | Files / lock only, **no** containers (replaces `--skip-start`) |
| `odpm init URL` | Project init (replaces `--init`) |
| `odpm build` | Final CI image via layered stages (replaces `--build-image`) |
| `odpm image …` | One layer: `base` / `platform` / `venv` / `deps` / `app` / `lint` + `ensure` |
| `odpm plan` | Dry-run of prepare steps |
| `odpm database …` | Host: `status` / `ensure-role` / `pull`. Stack: `backup` / `restore` / `drop` / `list` |
| `odpm modules …` | Diff / record-applied |
| `odpm run …` | Recipes |
| `odpm manifest …` | migrate / validate |
| `odpm scaffold …` | Module scaffold |
| `-V`, `--version` | odpm version (global) |

In **4.8**, bare `odpm` and legacy root flags still work with a **warning**. In **5.0**, bare `odpm` prints subcommand help (no stack up). See [Deprecated in 4.8](#deprecated-in-48).

## Project initialization

Preferred: **`odpm init URL`**. Deprecated synonym: `--init LINK`.

`odpm init` **starts the stack** by default (full run). For files-only init without compose up, use the **4.8** legacy combo `odpm --init URL --skip-start` (the `init` subcommand has no `--skip-start` flag).

| Parameter | Description |
|-----------|-------------|
| `odpm init LINK` / `--init LINK` | Make the current directory an odpm project. Link: HTTPS, `git@…`, `file:///…` |
| `--branch NAME` | With `--init`: branch of the **developing** repository |
| `--odoo-version VER` | Odoo version (e.g. `19.0`) in `odpm.json` |
| `--odoo-git-link LINK` | **Platform** repository instead of official odoo/odoo |
| `--platform-name NAME` | Fork Python package name (default `odoo`) |
| `--python-version VER` | Python version in the image |
| `--distro-name NAME` | Linux distribution name (currently `debian`) |
| `--distro-version VER` | Distribution version (`11`, `12`, …) |
| `--postgres-version VER` | PostgreSQL version in compose |
| `--requirements-txt PACKAGES` | Python packages comma-separated → written to `odpm.json` |
| `--secrets-file PATH` | Import JSON v1 into `.odpm/secrets.json` (on `--init` and any run; early bootstrap, before `${@secret:}` expand in `user_settings`). Implies the `file` provider. See [local secrets](../operations/secrets.md). |
| `--secrets-provider NAME` | Secrets provider for this run (`file`, `infisical`, or a plugin id). Overrides `ODPM_SECRETS_PROVIDER` and `secrets.provider.type`. `--secrets-file` forces `file`. |
| `--security-profile NAME` | Security profile (`convenience` / `hardened`). Overrides `ODPM_SECURITY_PROFILE`; else defaults from `ODPM_SCENARIO`. See [security](../operations/security.md). |

Example:

```bash
odpm init https://github.com/aayartsev/odoo_demo_project.git --branch 19.0 \
  --odoo-version 19.0 --python-version 3.12 --distro-version 12
```

Import secrets on deploy:

```bash
odpm init file:///path/to/my_addons \
  --secrets-file /secure/client-secrets.json

# key rotation on an existing project
odpm prepare --secrets-file ~/new-secrets.json
```

## Environment prepare and image

| Command / parameter | Description |
|---------------------|-------------|
| `odpm prepare` | Regenerate Docker files and compose **without** starting containers |
| `odpm prepare -d NAME` | Same, and bake `-d NAME` into the Odoo start command in compose (no `compose up`) |
| `odpm prepare --stop-after sources` | Sources snapshot only (git / links); no Docker, compose, or secrets |
| `odpm prepare --update-lock` | Write `.odpm/deps.lock.json` and exit |
| `--no-git-update` | Do not touch git; lock is **not read**; directories must already exist |
| `--git-worktree` | Materialize remote git as bare mirrors + per-tenant worktrees under `ODOO_PROJECTS_DIR` (same as `ODPM_GIT_WORKTREE=1`; ADR-028) |
| `odpm image <layer> ensure` | Ensure a CI image layer: `base`, `platform`, `venv`, `deps`, `app`, `lint` (ADR-027); **first** scoped prepare (sources + secrets + Dockerfile/dockerignore), **then** layer build — intentional coupling, no build-only mode |
| `odpm image … --from REF` | Explicit parent for `deps` / `app` (else venv or deps) |
| `odpm build` | Layered shortcut for **`ci`**: base → platform → venv → deps? → app (error otherwise) |
| `--image-tag TAG` | Final image name/tag for `build` / `image app ensure` |
| `--image-builder {docker,kaniko}` | CI image build backend (default `docker`) |
| `--image-push` | After build, publish the image (publish-tag alias after kaniko via `crane copy`) |
| `--image-prune-stale` | After a successful ensure, delete stale same-layer `cache-*` tags (same as `ODPM_IMAGE_PRUNE_STALE=1`) |
| `-V`, `--version` | Show odpm version |

CI flow: `prepare --stop-after sources` → `plan` (layer hit/miss) → `image … ensure` or `build`. Registry tag families: **dev** (profile `full`) and **runtime** (profile `medium`) via `ODPM_BASE_IMAGE_PROFILE`. Scenario `ci` and base profile `ci` are **not** renamed. See [ci scenario](../scenarios/ci.md), [ADR-027](https://github.com/aayartsev/odpm/blob/4.8.0-dev/docs/contributing/adr-027-layered-ci-images.md).

Deprecated synonyms: `--skip-start` → `odpm prepare`; `--build-image` → `odpm build` (layered chain).

## Change plan (dry run)

Shows which prepare steps would run **without** changing git, writing files, or `docker compose up`. The table groups steps with headers (git/sources, dependencies, folder map, templates, secrets, image build, runtime, …) — labels only; step ids are unchanged. Developing, platform, and dependency clones are separate rows; the folder map does not clone. When the stack would start, the runtime group shows **`runtime.ensure_base`** (base image) and **`compose.up`**; with `--skip-start` / prepare-only they are absent. Runtime engine contract: [ADR-029](https://github.com/aayartsev/odpm/blob/4.8.0-dev/docs/contributing/adr-029-runtime-backend.md).

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

Local **PostgreSQL cluster** inspection, application role repair, and **remote Odoo manager backup download**:

```bash
odpm database status
odpm database status --format json
odpm database ensure-role
ODPM_REMOTE_DB_MASTER_PWD='…' odpm database pull --url https://client.example.com --remote-db prod
```

| Command | Description |
|---------|-------------|
| `database status` | Fingerprints, drift, postgres container and application role checks |
| `database status --format json` | Same as JSON |
| `database ensure-role` | Create or update the application role in running PostgreSQL |
| `database pull` | Download a zip from `{URL}/web/database/backup` into `BACKUP_DIR` (password only via env `ODPM_REMOTE_DB_MASTER_PWD`) |

`database pull` is a **primitive**: needs an odpm project with `BACKUP_DIR` in `.env`; compose up is not required for the download. It calls `/web/database/list` when available, then the backup; auth/progress logs go to stderr, **stdout is only the archive file name** (basename under `BACKUP_DIR`). Compose further steps yourself (shell / CI), for example:

```bash
export ODPM_REMOTE_DB_MASTER_PWD='…'
ARCHIVE=$(odpm database pull --url https://client.example.com --remote-db prod)
odpm up -d test_db --db-restore "$ARCHIVE" -i -u --set-admin-pass
```

Shortcut for pull+restore without custom steps: builtin [`odpm run pull-remote-db`](recipes.md#builtin-pull-remote-db). YAML recipes **cannot** substitute a previous step’s stdout — use shell for archive-name chains. Intended for **developer** / **server**, not typical CI.

Flag **`--accept-database-drift=KIND`** (repeatable) — accept drift without an interactive prompt. KIND: `data_path`, `postgres_major`, `app_role_missing`, `odpm_scenario`, `data_dir_empty_changed`.

Local cluster details: [PostgreSQL state and drift](database-state.md). Remote pull: [recipes](recipes.md) (primitive + `pull-remote-db`).

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

## `modules` subcommand

Init/update module lists from developing git history and the last-applied deploy marker:

```bash
odpm modules diff
odpm modules diff --diff-base @last-applied --format shell
odpm modules record-applied
```

| Command | Description |
|---------|-------------|
| `modules diff` | Init/update CSV from `BASE...HEAD`; `--diff-base`, `--format {text,shell,json}` |
| `modules record-applied` | Write developing HEAD to `.odpm/deploy/last_applied.json` |

Details and shell recipe: [deploy marker](deploy-marker.md).

## `run` subcommand

Named recipes (re-exec odpm steps):

```bash
odpm run --list
odpm run apply-modules-from-diff -d prod_db
odpm run apply-modules-from-diff -d prod_db --dry-run
```

Details: [recipes](recipes.md), [deploy marker](deploy-marker.md).

## Database and modules

| Parameter | Description |
|-----------|-------------|
| `-d DB_NAME` | Database name; if missing — creation per `db_creation_data` |
| `-i [MODULES]` | Without a value — modules from `init_modules`; with a CSV (e.g. `sale,crm`) — CLI list (overrides settings for this run) |
| `-u [MODULES]` | Without a value — modules from `update_modules`; with a CSV — CLI list (overrides settings for this run) |
| `-t`, `--test` | Run module tests; requires `-d` and usually `-i` or `-u` |
| `--screencasts` | With `-t`: save video on tour failures |
| `--odoo-bin ARGS…` | Pass arguments to the Odoo executable, e.g. `--stop-after-init` |

```bash
odpm up -d test_db -i -u
odpm up -d test_db -i sale,crm -u my_module
odpm up -d test_db -i --odoo-bin --stop-after-init
```

The same image can start against different databases. The container command begins with `python3 -m dev_project.inside_docker_app.run_odoo --`, then the `odoo-bin` arguments. The name after `-d` or `--database` on that command is the database the container creates when it is missing and then opens. It overrides `arguments.d` in the mounted `.odpm/runtime/config.json`. The settings file is still required: it holds paths, PostgreSQL access, and database creation parameters. Do not change the database name in that file — the start command sets it. An external script or a Kubernetes pod passes its own `-d` and does not rebuild the image.

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
| `--export-po-files LANG` | Export pot/po for modules from `update_modules`, or from `-u CSV` when that form is used |
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

## Deprecated in 4.8

Legacy invocations still work and print a warning. Preferred forms:

| Deprecated | Preferred |
|------------|-----------|
| bare `odpm` | `odpm up` (in **5.0** bare `odpm` → subcommand help) |
| `odpm -d … -i …` | `odpm up -d … -i …` |
| `odpm --skip-start` | `odpm prepare` |
| `odpm --init URL` | `odpm init URL` |
| `odpm --build-image` | `odpm build` |
| `odpm --plan` | `odpm plan` |
| single `--db-backup` / `--db-restore` / `--db-drop` / `--get-dbs-list` | `odpm database backup\|restore\|drop\|list` |
| `--db-drop --db-restore …` or restore+`-i` | `odpm up …` |

Contract: [ADR-026](https://github.com/aayartsev/odpm/blob/4.8.0-dev/docs/contributing/adr-026-cli-command-verbs.md) (Russian).
