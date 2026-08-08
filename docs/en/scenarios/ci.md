# Continuous integration scenario (`ci`)

> **AI-translated** from Russian.

The **`ODPM_SCENARIO=ci`** variable prepares a **ready-made Docker image** of the project: platform sources, addons, Python environment, and configuration are **baked into the image**; Odoo directories are **not mounted** from the build machine disk.

## Purpose

The build engineer or automation pipeline gets a **reproducible artifact**: the same code and the same pinned git revisions described in `odpm.json` and `.odpm/deps.lock.json`. After the build, the image can be published to a registry and deployed to stands using tools already adopted in the organization.

odpm **does not replace** GitHub Actions, GitLab CI, or orchestrators — it provides an **image build command** and a consistent way to run Odoo with the same parameters as the developer and administrator.

## Environment behavior

| Area | How it works |
|------|--------------|
| **Image** | Created with `odpm --build-image` (available **only** in this scenario). Backend: `docker` (default) or `kaniko` — see [ADR-016](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-016-ci-image-build-backends.md). |
| **Sources** | Inside the image, no host mount. |
| **Python environment** | Built during image build, not recreated on every `up`. |
| **Debugger** | None. |
| **Module secrets** | Host mount **disabled**. Optional bake into image: `ODPM_BAKE_SECRETS=1` with `--build-image` — see [local secrets](../operations/secrets.md), [ADR-002](https://github.com/aayartsev/odpm/blob/4.4-dev/docs/contributing/adr-002-ci-secrets-bake.md). |
| **Version pinning** | Strict check of `.odpm/deps.lock.json`; version incompatibilities in nested manifests — **error**. |
| **Python warnings in logs** | Same as `server`: `PYTHONWARNINGS` is not filtered — `DeprecationWarning` from docutils on Odoo startup remain in build and container output. Account for this in CI logs and image smoke tests. |
| **Base image** | Profile **ci** (slim Dockerfile). With `kaniko`, local `ensure_base_image` is **skipped** — the base tag must be pullable from a registry. |

## Typical pipeline

```text
git push → build machine
  → ODPM_SCENARIO=ci
  → odpm --skip-start
  → odpm --build-image [--image-tag registry/project:tag] [--image-builder docker|kaniko] [--image-push]
  → publish image (or --image-push / kaniko tar artifact)
  → deploy (your tools)
```

## Checklist

1. In git: `odpm.json` and committed `.odpm/deps.lock.json`.
2. On the build machine: odpm, `.env` with `ODPM_SCENARIO=ci`; for `docker` — Docker daemon; for `kaniko` — executor (`docker-run` or `direct`) and a registry-pullable base.
3. Before merge: `odpm plan --strict` — exit code 1 on unexpected changes.
4. Verification: HTTP 200 on `/web` after `docker compose up`.

## Command examples

```bash
export ODPM_SCENARIO=ci
odpm --skip-start
# optional: odpm --secrets-file /secure/ephemeral.json --skip-start
export ODPM_BAKE_SECRETS=1   # bake module secrets into image when secrets.json exists
odpm --build-image --image-tag myregistry/client-odoo:19.0
odpm --build-image --image-builder kaniko --image-tag myregistry/client-odoo:19.0 --image-push
ODPM_CI_IMAGE_BUILDER=kaniko ODPM_KANIKO_EXECUTOR_MODE=direct \
  odpm --build-image --image-tag myregistry/client-odoo:19.0 --image-push
docker compose up -d
odpm -d test_db -i --odoo-bin --stop-after-init
```

Without `--image-push`, the `kaniko` backend writes a tar to `.odpm/ci-build-context/odpm-ci-image.tar`.

In `docker-run` mode with `--image-push`, `~/.docker/config.json` is required (`docker login`); otherwise odpm fails before starting the executor. The default executor image is pinned (`gcr.io/kaniko-project/executor:v1.23.2`); override with `ODPM_KANIKO_EXECUTOR_IMAGE`. Opt-in Docker integration in CI covers the `docker` backend only; `kaniko` argv/`direct` paths are covered by unit tests.

Non-interactive initialization:

```bash
export ODPM_SCENARIO=ci
export ODOO_PROJECTS_DIR=/data/odoo_projects
export BACKUP_DIR=/data/backups
odpm --init https://github.com/aayartsev/odoo_demo_project.git --branch 19.0 --skip-start
```

See [non-interactive runs](../operations/non-interactive.md).
