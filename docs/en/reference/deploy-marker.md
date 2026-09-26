# Deploy marker (module apply)

File **`.odpm/deploy/last_applied.json`** stores the developing-repo SHA of the last successful `-i`/`-u` apply. It is **not** part of `odpm.json` and not a dependency lock.

## Location

| Path | Purpose |
|------|---------|
| `{project_dir}/.odpm/deploy/last_applied.json` | Marker on the **odpm project host dir** (where `docker-compose.yml` lives), not necessarily the developing git root |
| `.odpm/.gitignore` → `deploy/` | Written on first `record-applied` / marker use |

JSON fields:

```json
{
  "developing_sha": "abc123…",
  "applied_at": "2026-09-27T10:00:00Z"
}
```

No `db_name` in the marker: one SHA per project instance.

## Subcommands

```bash
odpm modules diff
odpm modules diff --diff-base @last-applied --format shell
odpm modules diff --diff-base origin/main --format json
odpm modules record-applied
```

| Command | Description |
|---------|-------------|
| `modules diff` | Init/update lists from `git diff BASE...HEAD` in developing |
| `modules record-applied` | Write developing HEAD into the marker (no compose) |

`--format` values: **`text`** (default), **`shell`** (`export ODPM_INIT_MODULES=…` / `ODPM_UPDATE_MODULES=…`), **`json`**. Lists go to **stdout**; logs use stderr/logger so `eval "$(…)"` stays clean.

## Baseline

Priority when `--diff-base` is omitted:

1. `ODPM_DIFF_BASE`
2. `CI_MERGE_REQUEST_DIFF_BASE_SHA` (GitLab MR)
3. SHA from the marker if the file exists
4. otherwise **error** — lists are never invented without a baseline

`--diff-base @last-applied` forces the marker (error if missing). First deploy: pass an explicit `--diff-base <sha|tag>` (or env), apply modules, then `record-applied`.

Repo: **developing** checkout with `.git` only. Deleted modules are ignored; rename → new path as init if the module did not exist at BASE.

## Apply recipe (shell)

Do **not** pass empty lists as `-i ""` / `-u ""` — the CLI rejects empty CSV.

```bash
eval "$(odpm modules diff --diff-base @last-applied --format shell)"

args=(-d prod_db)
[[ -n "${ODPM_INIT_MODULES}" ]] && args+=(-i "${ODPM_INIT_MODULES}")
[[ -n "${ODPM_UPDATE_MODULES}" ]] && args+=(-u "${ODPM_UPDATE_MODULES}")
odpm "${args[@]}" --odoo-bin --stop-after-init

# only after exit 0
odpm modules record-applied
```

A long-running `docker compose up` **without** `--stop-after-init` cannot drive automatic marker updates: run `record-applied` only after a successful apply.

## CI / MR

Set the baseline via `--diff-base` or `CI_MERGE_REQUEST_DIFF_BASE_SHA` / `ODPM_DIFF_BASE`. The `modules` subcommand is on the CI allowlist (like `plan` / `database` / `manifest`).

## Out of scope for v1

No one-shot `--modules-from-git-diff` orchestrator and no generic `odpm run` / recipes framework — subcommands plus this documented shell recipe only.
