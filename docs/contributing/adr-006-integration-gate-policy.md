# ADR-006: Integration gate policy (4.5)

**Status:** accepted (4.5-dev)  
**Date:** 2026-06-22

## Context

odpm 4.4 established a **fast** mandatory gate (`compose-smoke` on `ubuntu-latest`) and an **opt-in** full golden-path (`init` → `docker compose up` → HTTP 200 `/web`) on a self-hosted runner with secret `ODPM_GOLDEN_PATH_PROJECT`.

Phase I1 (4.5) requires a **mandatory integration gate on every PR** to `4.5-dev` without depending on a single maintainer machine, while keeping compose-smoke under ~5 minutes as the primary fast check.

## Decision

### Three-tier integration policy

| Tier | Job | Runner | Trigger | Gate |
|------|-----|--------|---------|------|
| **T1 — fast** | `compose-smoke` | `ubuntu-latest` | every push/PR | **required** — `odpm --skip-start`, `docker compose config`, v1 + Mailpit manifest |
| **T2 — HTTP** | `http-smoke` | `ubuntu-latest` | every push/PR | **required** (4.5-dev) — in-repo minimal fixture, `compose up mailpit`, HTTP 200 |
| **T3 — full** | `golden-path` | self-hosted | nightly, `workflow_dispatch`, label `run-docker` | opt-in; **required** on pre-release tags via `release-packages.yml` |

T2 is the **ephemeral GHA** substitute for mandatory golden-path on PRs. T3 remains the full Odoo `/web` E2E on a real initialized project.

### Environment flags

| Variable | Job | Meaning |
|----------|-----|---------|
| `ODPM_RUN_DOCKER_COMPOSE_SMOKE=1` | compose-smoke | enable compose smoke tests |
| `ODPM_COMPOSE_SMOKE_MAILPIT=1` | compose-smoke | manifest v2 Mailpit fragment |
| `ODPM_RUN_HTTP_SMOKE=1` | http-smoke | enable HTTP smoke test |
| `ODPM_COMPOSE_SMOKE_PLUGIN=1` | compose-smoke | sample_plugin + Mailpit E2E |
| `ODPM_COMPOSE_SMOKE_HOOKS=1` | compose-smoke | shell + Python hook E2E |
| `ODPM_RUN_FIXTURE_GOLDEN_PATH=1` | weekly | in-repo fixture Odoo `/web` |
| `ODPM_RUN_DOCKER_INTEGRATION=1` | golden-path / weekly | enable full golden-path / CI image build |
| `ODPM_GOLDEN_PATH_ENABLED` | repo variable | gate self-hosted golden-path jobs |
| `ODPM_GOLDEN_PATH_PROJECT` | secret | path to real project on self-hosted runner |

### Branch protection (`4.5-dev`)

Required status checks: **lint**, **unit**, **contract**, **compose-smoke**, **http-smoke**.

Maintainers configure checks in GitHub UI or `gh api` (see `docs/contributing/ci.md`).

### Path filters

Not used in 4.5.0 — integration jobs run on every PR to `4.5-dev`. Future optimization may scope `http-smoke` to `dev_project/`, `tests/`, `docker` templates.

### Fallback and flakes

- T1 failure blocks merge; T2 provides runtime confidence beyond `compose config`.
- T3 failures on pre-release tags block publish (unchanged).
- **Retry policy (I3):** re-run failed Docker jobs once in GitHub UI; `docker pull` / registry flakes — wait 5–10 minutes; local: `docker compose down` then re-run the matching `scripts/run_*` helper.
- **Artifacts (I3):** on failure, `http-smoke` and `golden-path` upload `/tmp/odpm-compose-debug/` (compose logs + `docker-compose.yml`) when `ODPM_COMPOSE_DEBUG_DIR` is set in CI.
- **Timeouts (I3):** job timeout must exceed env timeout + startup buffer. `venv_lock_hash` includes a SHA-256 of Odoo `requirements.txt` (since 4.6) so venv rebuilds when platform deps change without bumping `odoo_version`.

| Job | GHA `timeout-minutes` | Env timeout | Notes |
|-----|----------------------|-------------|-------|
| `compose-smoke` | 20 | `ODPM_COMPOSE_SMOKE_TIMEOUT=900` | T1 fast gate |
| `http-smoke` | 25 | `ODPM_HTTP_SMOKE_TIMEOUT=600` | T2 Mailpit HTTP |
| `golden-path` | 15 | `ODPM_GOLDEN_PATH_TIMEOUT=90` | T3 self-hosted |
| `fixture-golden-path` (weekly) | 45 | `ODPM_FIXTURE_GOLDEN_TIMEOUT=900` | I2 in-repo `/web` |

### I2 — extended matrix (weekly + PR steps)

| Check | Where | Trigger |
|-------|-------|---------|
| Plugin E2E (`sample_plugin` + Mailpit) | `compose-smoke` job | every PR |
| Hooks E2E (shell + local Python) | `compose-smoke` job | every PR |
| Fixture golden-path `/web` | `ci-integration-weekly.yml` | weekly + dispatch |
| CI image `docker build` | `ci-integration-weekly.yml` | weekly + dispatch |
| `.deb` install smoke | `ci-integration-weekly.yml` | weekly + dispatch |

## Consequences

- `.github/workflows/ci-docker.yml` gains mandatory `http-smoke` job.
- `tests/integration/test_http_smoke.py` uses `tests/fixtures/minimal_odpm_project` + Mailpit service.
- `scripts/run_http_smoke_test.sh` mirrors CI flags.
- Full golden-path on every PR is **not** required when T2 is green (documented here and in `ci.md`).
