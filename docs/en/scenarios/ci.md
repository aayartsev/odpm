# Continuous integration scenario (`ci`)

> **AI-translated** from Russian.

The **`ODPM_SCENARIO=ci`** variable prepares a **ready-made Docker image** of the project: platform sources, addons, Python environment, and configuration are **baked into the image**; Odoo directories are **not mounted** from the build machine disk.

## Purpose

The build engineer or automation pipeline gets a **reproducible artifact**: the same code and the same pinned git revisions described in `odpm.json` and `.odpm/deps.lock.json`. After the build, the image can be published to a registry and deployed to stands using tools already adopted in the organization.

odpm **does not replace** GitHub Actions, GitLab CI, or orchestrators — it provides an **image build command** and a consistent way to run Odoo with the same parameters as the developer and administrator.

## Environment behavior

| Area | How it works |
|------|--------------|
| **Image** | Layered build (ADR-027): `odpm prepare --stop-after sources` → miss analysis → `odpm image <layer> ensure` or shortcut `odpm build` (base → platform → deps? → app). Available **only** in this scenario. Backend: `docker` / `kaniko` — [ADR-016](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-016-ci-image-build-backends.md). |
| **Layer families** | Registry tags: **dev** ↔ base profile `full` (browser); **runtime** ↔ `medium` (wkhtml, no browser). Set via `ODPM_BASE_IMAGE_PROFILE`. Scenario `ci` and profile `ci` are **not** renamed. |
| **Sources** | Host snapshot first (`--stop-after sources`); final image has no host mount. |
| **Python environment** | Bake venv in the **platform** layer, not in app. |
| **Debugger** | None. |
| **Module secrets** | Host mount **disabled**. Optional bake into image: `ODPM_BAKE_SECRETS=1` with `--build-image` — see [local secrets](../operations/secrets.md), [ADR-002](https://github.com/aayartsev/odpm/blob/4.4-dev/docs/contributing/adr-002-ci-secrets-bake.md). |
| **Version pinning** | Strict check of `.odpm/deps.lock.json`; version incompatibilities in nested manifests — **error**. |
| **Python warnings in logs** | Same as `server`: `PYTHONWARNINGS` is not filtered — `DeprecationWarning` from docutils on Odoo startup remain in build and container output. Account for this in CI logs and image smoke tests. |
| **Base image** | Default profile **ci** (slim Dockerfile). Override with `ODPM_BASE_IMAGE_PROFILE` = `full` / `medium` / `ci` — see [ADR-007](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-007-base-image-profiles.md). With `kaniko`, base is built and **pushed** to `ODPM_BASE_IMAGE_REGISTRY` (ADR-019); final `FROM` uses that registry ref. Kaniko “exists” uses the local identity stamp (not a registry probe); if the registry image was deleted, remove `.odpm/base_image_identity.json` and rebuild. |

## Typical pipeline

```text
git push → build machine
  → ODPM_SCENARIO=ci
  → ODPM_BASE_IMAGE_PROFILE=full   # family dev; or medium → runtime
  → odpm prepare --stop-after sources
  → odpm plan                      # fingerprints / layer hit-miss
  → odpm image base ensure
  → odpm image platform ensure
  → odpm image deps ensure         # noop when no dependencies
  → odpm image app ensure --image-tag registry/project:tag [--image-push]
  # or shortcut:
  → odpm build [--image-tag …] [--image-builder docker|kaniko] [--image-push]
  → optional: odpm image lint ensure   # bake pre-commit hook cache (needs network)
  → deploy (your tools)
```

`odpm image lint ensure` builds a layer `FROM` platform and **warms the hook cache** (`pre-commit install-hooks` inside the image, cache under the container user home). Git for bake uses an isolated `.odpm-lint-bake` directory, not the platform tree at home root. It does **not** run `pre-commit run --all-files` on application code — that stays for a later job. Cold ensure needs network on the builder (hook repo clones).

`odpm image … ensure` does not run the `template.odoo_conf` prepare step, but before writing the build context it calls `generate_odoo_conf_docker_data` (after refreshing secrets and reloading the manifest). The **app** layer must ship `odoo_config_data.options` in `/run/odpm/config.json` (including `db_*` from the effective `ci` slice with expanded `${@secret:…}`).

Remote layer presence checks require **`crane digest`** (fail-fast otherwise). Publishing a publish-tag alias after kaniko (`--image-push` / `ODPM_CI_IMAGE_PUSH`, when the fingerprint cache image is not in the local Docker daemon) requires **`crane copy`**. Force rebuild of the current layer: `ODPM_IMAGE_FORCE_REBUILD=1`. Optional prune of stale same-layer `cache-*` tags after a successful ensure: `ODPM_IMAGE_PRUNE_STALE=1` or `--image-prune-stale` (keeps the current fingerprint tag; never touches floating `mr-*` / publish tags; missing crane for remote prune is fail-soft with a log line).

## Checklist

1. In git: `odpm.json` and committed `.odpm/deps.lock.json`.
2. On the build machine: odpm, `.env` with `ODPM_SCENARIO=ci`; for `docker` — Docker daemon; for `kaniko` — executor (`direct` recommended), `ODPM_BASE_IMAGE_REGISTRY`, and credentials for push/pull.
3. Before merge: `odpm plan --strict` — exit code 1 on unexpected changes.
4. Verification: HTTP 200 on `/web` after `docker compose up`.

## Command examples

```bash
export ODPM_SCENARIO=ci
export ODPM_BASE_IMAGE_PROFILE=full   # family dev
odpm prepare --stop-after sources
odpm plan
odpm image platform ensure
odpm image app ensure --image-tag myregistry/client-odoo:19.0 --image-push
# optional: odpm prepare --secrets-file /secure/ephemeral.json
export ODPM_BAKE_SECRETS=1   # bake module secrets into app layer when secrets.json exists
odpm build --image-tag myregistry/client-odoo:19.0
odpm build --image-builder kaniko --image-tag myregistry/client-odoo:19.0 --image-push
ODPM_IMAGE_PRUNE_STALE=1 odpm image app ensure --image-tag myregistry/client-odoo:19.0 --image-push
odpm build --image-tag myregistry/client-odoo:19.0 --image-prune-stale
ODPM_CI_IMAGE_BUILDER=kaniko ODPM_KANIKO_EXECUTOR_MODE=direct \
  ODPM_BASE_IMAGE_REGISTRY=registry.example.com/odpm \
  odpm build --image-tag myregistry/client-odoo:19.0 --image-push
docker compose up -d
# Module install after stack is up (bare `odpm up -d/-i` / legacy root flags is rejected in ci).
# Physical odoo key from docker-compose.yml (odoo / acme-odoo / odoo-dev / …):
ODOO_SVC=odoo
docker compose exec "$ODOO_SVC" odoo-bin -d test_db -i base --stop-after-init
```

In the `ci` scenario, `odpm up`, `scaffold`, and stack `database backup|restore|drop|list` are rejected. Allowed: `prepare` / `build` / **`image`** / `init` / `plan` / `manifest` / `modules` / `run` / host-`database` / `--version`/`-V` (plus legacy synonyms) — see [ADR-017](https://github.com/aayartsev/odpm/blob/4.8.0-dev/docs/contributing/adr-017-ci-prepare-only-policy.md), [ADR-026](https://github.com/aayartsev/odpm/blob/4.8.0-dev/docs/contributing/adr-026-cli-command-verbs.md), [ADR-027](https://github.com/aayartsev/odpm/blob/4.8.0-dev/docs/contributing/adr-027-layered-ci-images.md).

## External PostgreSQL in `ci` (ADR-022)

The effective `ci` slice may set `db_*` in `odoo_conf.options` (still forbidden in `developer` / `server`). Prefer `${@secret:…}` for credentials:

```json
"scenarios": {
  "ci": {
    "odoo_conf": {
      "options": {
        "db_host": "10.241.2.102",
        "db_port": 5000,
        "db_user": "${@secret:pg_user}",
        "db_password": "${@secret:pg_user_password}",
        "proxy_mode": "True",
        "server_wide_modules": "base,web,queue_job"
      }
    }
  }
}
```

Values reach `odoo_config_data` via the normal merge (disk → manifest), including when building the app image via `image app ensure`. The compose `db` service is not removed; host-side `odpm database` / `ensure_app_role` still target compose postgres. See [odoo.conf](../reference/odoo-conf.md), [ADR-022](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-022-odoo-conf-scenario-frozen.md).

Without `--image-push`, the `kaniko` backend writes a tar to `.odpm/ci-build-context/odpm-ci-image.tar`.

In `docker-run` mode with `--image-push`, `~/.docker/config.json` is required (`docker login`); otherwise odpm fails before starting the executor. The default executor image is pinned (`gcr.io/kaniko-project/executor:v1.23.2`); override with `ODPM_KANIKO_EXECUTOR_IMAGE`. Opt-in Docker integration in CI covers the `docker` backend only; `kaniko` argv/`direct` paths are covered by unit tests.

For **`direct`** on a **non-root** build user, odpm does not run as root but Kaniko executor often needs privileges. Set **`ODPM_KANIKO_EXECUTOR_WRAPPER`** to a script that launches the executor as root (recommended), or **`ODPM_KANIKO_EXECUTOR_SUDO=1`** with passwordless sudo for the executor binary. Optional **`ODPM_KANIKO_EXECUTOR_EXTRA_FLAGS`** (e.g. `--kaniko-dir=/tmp/kaniko`) adjusts Kaniko runtime paths. See [ADR-016](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-016-ci-image-build-backends.md).

Non-interactive initialization:

```bash
export ODPM_SCENARIO=ci
export ODOO_PROJECTS_DIR=/data/odoo_projects
export BACKUP_DIR=/data/backups
# init without compose up (4.8 legacy combo; plain odpm init starts the stack)
odpm --init https://github.com/aayartsev/odoo_demo_project.git --branch 19.0 --skip-start
```

See [non-interactive runs](../operations/non-interactive.md).
