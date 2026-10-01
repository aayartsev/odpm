# Recipes (`odpm run`)

The **recipe** layer binds CLI/env parameters and runs an ordered series of **odpm re-exec** subprocesses without mutating the current process flags.

Use it for flows like “diff modules → `-i`/`-u` → write marker” on **server**. Hooks/plugins stay in-process and do not replace this layer.

## Commands

```bash
odpm run --list
odpm run apply-modules-from-diff -d prod_db
odpm run apply-modules-from-diff -d prod_db --diff-base @last-applied --dry-run
odpm run pull-remote-db -d local_copy --url https://client.example.com --remote-db prod
```

| Flag | Description |
|------|-------------|
| `--list` | List recipes (builtins + `.odpm/recipes/*.yaml`) |
| `--dry-run` | Print argv plan; for `apply-modules-from-diff` still runs `modules diff` (capture); apply/record are not spawned; for `pull-remote-db` **no** network calls |
| `-d` | Database name (param `database`; else env `ODPM_RUN_DATABASE`) |
| `--diff-base` | Baseline for recipes that support `diff_base` |
| `--url` | Remote Odoo URL for recipes that support `url` (else env `ODPM_REMOTE_DB_URL`) |
| `--remote-db` | Remote DB name for recipes that support `remote_db` (else env `ODPM_REMOTE_DB_NAME`) |

## Discovery

1. Python builtins (odpm package), currently: `apply-modules-from-diff`, `pull-remote-db`
2. Project: `{project_dir}/.odpm/recipes/<name>.yaml` — **overrides** a builtin with the same name

Do not override builtins unless you intend to.

## Builtin: `apply-modules-from-diff`

Intended for **`ODPM_SCENARIO=server`** (and manual developer use).

1. `odpm modules diff [--diff-base] --format json`
2. If init/update non-empty: `odpm -d … [-i …] [-u …] --odoo-bin --stop-after-init`
3. `odpm modules record-applied` (also when both lists are empty — advance baseline)

Empty `-i`/`-u` flags are never passed. Long-running compose without `--stop-after-init` is out of scope for this recipe.

### CI

Under `ODPM_SCENARIO=ci`, end-to-end apply via `odpm run` is **not** supported (child `odpm -d -i/-u` is not CI-allowlisted). In CI use `odpm modules diff`; run apply on server.

## Builtin: `pull-remote-db`

Shortcut for **`developer` / `server`**: **pull + `--db-restore` only**. Does not install/update modules or reset the admin password.

```bash
export ODPM_REMOTE_DB_MASTER_PWD='…'   # remote DB manager master password
odpm run pull-remote-db -d local_copy \
  --url https://client.example.com \
  --remote-db prod
```

1. `odpm database pull --url … --remote-db …` → file under `BACKUP_DIR` (password from env only; stdout is the archive name)
2. `odpm -d … --db-restore <archive>` — full prepare/runtime, same as a normal restore

`--dry-run` prints argv **without** network I/O. Do not commit the master password to git. Default HTTP timeout is 600s (tool); recipe steps use no subprocess timeout limit.

Requires an odpm project directory with `BACKUP_DIR` configured. A typical CI pull+restore flow is **not** a product goal.

## Compose a pipeline from primitives (canonical)

`odpm database pull` is a low-level step: download a zip and print its name. Further steps (**restore**, `-i`/`-u`, `--set-admin-pass`, …) belong in **shell** (or a CI job), not in one oversized `odpm run`.

```bash
export ODPM_REMOTE_DB_MASTER_PWD='…'
ARCHIVE=$(odpm database pull \
  --url https://client.example.com \
  --remote-db prod)
odpm -d test_db --db-restore "$ARCHIVE" -i -u --set-admin-pass
```

Two-call equivalent when the builtin restore shortcut is enough:

```bash
odpm run pull-remote-db -d test_db --url https://client.example.com --remote-db prod
odpm -d test_db -i -u --set-admin-pass
```

Why not YAML: v1 only substitutes `${param.*}` / `${env:…}` and **cannot** feed a step’s stdout into the next argv. For archive-name chains use shell (or a custom Python recipe).

See also [CLI: `database pull`](cli.md) and [database state](database-state.md).

## YAML recipes (v1)

Linear steps only (no conditionals). Substitutions: `${param.name}`, `${env:VAR}` — **no** previous-step stdout capture.

```yaml
name: example-backup
description: Backup then skip-start
params:
  database:
    required: true
    env: ODPM_RUN_DATABASE
steps:
  - odpm: ["-d", "${param.database}", "--db-backup"]
  - odpm: ["--skip-start"]
```

Place the file in `.odpm/recipes/example-backup.yaml`. A step must not start with `run` (recursion guard).

## Execution model

Phased: `next_step(ctx)` → subprocess → result into context → `next_step` again. Per step: `capture` (JSON) or live stream; fail-fast on non-zero exit.
