# Recipes (`odpm run`)

The **recipe** layer binds CLI/env parameters and runs an ordered series of **odpm re-exec** subprocesses without mutating the current process flags.

Use it for flows like “diff modules → `-i`/`-u` → write marker” on **server**. Hooks/plugins stay in-process and do not replace this layer.

## Commands

```bash
odpm run --list
odpm run apply-modules-from-diff -d prod_db
odpm run apply-modules-from-diff -d prod_db --diff-base @last-applied --dry-run
```

| Flag | Description |
|------|-------------|
| `--list` | List recipes (builtins + `.odpm/recipes/*.yaml`) |
| `--dry-run` | Print argv plan; for `apply-modules-from-diff` still runs `modules diff` (capture); apply/record are not spawned |
| `-d` | Database name (param `database`; else env `ODPM_RUN_DATABASE`) |
| `--diff-base` | Baseline for recipes that support `diff_base` |

## Discovery

1. Python builtins (odpm package), currently: `apply-modules-from-diff`
2. Project: `{project_dir}/.odpm/recipes/<name>.yaml` — **overrides** a builtin with the same name

Do not override `apply-modules-from-diff` unless you intend to.

## Builtin: `apply-modules-from-diff`

Intended for **`ODPM_SCENARIO=server`** (and manual developer use).

1. `odpm modules diff [--diff-base] --format json`
2. If init/update non-empty: `odpm -d … [-i …] [-u …] --odoo-bin --stop-after-init`
3. `odpm modules record-applied` (also when both lists are empty — advance baseline)

Empty `-i`/`-u` flags are never passed. Long-running compose without `--stop-after-init` is out of scope for this recipe.

### CI

Under `ODPM_SCENARIO=ci`, end-to-end apply via `odpm run` is **not** supported (child `odpm -d -i/-u` is not CI-allowlisted). In CI use `odpm modules diff`; run apply on server.

## YAML recipes (v1)

Linear steps only (no conditionals). Substitutions: `${param.name}`, `${env:VAR}`.

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
