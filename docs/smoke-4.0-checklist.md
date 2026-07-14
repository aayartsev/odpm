# Smoke checklist: odpm 4.0 stable gate

Manual verification protocol before tagging **4.0.0**. Fill in **Result** and **Date** when you run each step on your machine. Do not commit paths to private customer projects — keep detailed notes in a local file (see [Local notes](#local-notes)).

## Variables

Set these in your shell before running project-scoped steps:

```bash
export ODPM_REPO=/path/to/odpm   # clone of this repository
export ODPM_PROJECT=/path/to/your-odpm-env   # initialized odpm project directory
export ODPM_SCENARIO=developer                 # or server / ci as required
```

Optional for integration scripts:

```bash
export ODPM_GOLDEN_PATH_PROJECT="$ODPM_PROJECT"
export ODPM_RUN_DOCKER_INTEGRATION=1         # required for docker integration tests
```

Use `odpm` after `pip install`, or `python3 "$ODPM_REPO/odpm.py"` in legacy copy mode.

---

## 2A — Unit baseline (odpm repository)

Automated on every push/PR to `4.0-beta` or `main`: GitHub Actions workflow [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) (Python 3.10 and 3.12).

Run locally from **`$ODPM_REPO`**:

```bash
cd "$ODPM_REPO"
python3 -m unittest discover -s tests -p "test_*.py"
```

| Check | Expected | Result | Date |
|-------|----------|--------|------|
| GitHub Actions `CI` | Green on push/PR; same command as local §2A | | |
| Test suite | All tests OK; 7 skipped (opt-in Docker unless `ODPM_RUN_DOCKER_*` env) | | |
| Test count | **634** tests OK (7 skipped by default); re-run after adding tests | | |

**Branch protection (recommended):** require GitHub status checks **CI** (unit) and **CI Docker** / **compose-smoke** on `4.0-beta` / `main` before merge. Full **golden-path** is opt-in (not required on every PR). Canonical policy: [contributing/ci.md](../contributing/ci.md).

---

## 2A+ — Docker CI (compose smoke + golden-path)

See [contributing/ci.md](../contributing/ci.md) for the full table. Summary:

| Job | Workflow | Trigger | Merge gate | Inputs |
|-----|----------|---------|------------|--------|
| **unit** | `ci.yml` | every push/PR | recommended | `tests/`; Python 3.10 + 3.12 |
| **contract** | `ci.yml` | every push/PR | recommended | `tests.test_manifest_contract` (manifest v2, extensions, plan locks) |
| **compose-smoke** | `ci-docker.yml` | every push/PR | recommended | [`tests/fixtures/minimal_odpm_project/`](../tests/fixtures/minimal_odpm_project/); Python 3.12 |
| **compose-smoke-mailpit** | `ci-docker.yml` (step in `compose-smoke` job) | every push/PR | recommended | manifest v2 + `services.mailpit`; `ODPM_COMPOSE_SMOKE_MAILPIT=1` |
| **golden-path** | `ci-docker.yml` | nightly, `workflow_dispatch`, PR label `run-docker` | opt-in | Self-hosted runner; variable `ODPM_GOLDEN_PATH_ENABLED=true` + secret `ODPM_GOLDEN_PATH_PROJECT`; skipped when variable unset |

**Compose smoke** — automated on every push/PR: [`.github/workflows/ci-docker.yml`](../.github/workflows/ci-docker.yml) (`compose-smoke` job; unit tests in [`ci.yml`](../.github/workflows/ci.yml)).

Local run from **`$ODPM_REPO`** (requires Docker):

```bash
cd "$ODPM_REPO"
./scripts/run_compose_smoke_test.sh
```

| Check | Expected | Result | Date |
|-------|----------|--------|------|
| GitHub Actions `CI Docker` → compose-smoke | Green on push/PR | | |
| GitHub Actions `CI Docker` → compose-smoke-mailpit | Green on push/PR (manifest v2 + Mailpit step in same job) | | |
| `odpm --skip-start` on minimal fixture | Exit 0 | | |
| `docker compose config` | Exit 0; `services:` in output | | |

**Golden-path** (compose up + HTTP 200): `ODPM_GOLDEN_PATH_PROJECT=/path/to/your-odpm-env ./scripts/run_golden_path_test.sh` locally; in CI — self-hosted runner, secret `ODPM_GOLDEN_PATH_PROJECT`, nightly, **workflow_dispatch** with golden flag, or PR label **`run-docker`** when `ODPM_GOLDEN_PATH_ENABLED=true` (see [contributing/ci.md](../contributing/ci.md)). Re-run **CI Docker** manually after adding `run-docker` to a PR.

**Troubleshooting compose smoke**

| Symptom | Likely cause | Action |
|---------|----------------|--------|
| First CI run > 10 min | Cold Docker cache; base image build | Normal; later runs use `actions/cache` image tar |
| `set ODPM_RUN_DOCKER_COMPOSE_SMOKE=1` skip locally | Opt-in env not set | `./scripts/run_compose_smoke_test.sh` |
| `docker not available` | Docker daemon not running | Start Docker; re-run |
| Timeout on CI | Slow image build | Raise `ODPM_COMPOSE_SMOKE_TIMEOUT` or fix cache key paths |

---

## 2B — Developer smoke (3.x → 4.0 compose migration)

Use a **real** odpm project directory that was on 3.x compose or an old 4.0-beta template.

**Legacy markers to replace:** `bash -c`, `main.py --config-base64-data`, compose `healthcheck`, placeholders `{START_STRING}`, `{MAPPED_VOLUMES}`, `{DEBUGGER_PORT_MAP}`.

```bash
cd "$ODPM_PROJECT"
odpm --skip-start
# review docker-compose.yml, then:
docker compose up -d
curl -sf "http://127.0.0.1:${ODOO_PORT:-8069}/web"
```

| Check | Expected | Result | Date |
|-------|----------|--------|------|
| `odpm --skip-start` | Exit 0; templates regenerated | | |
| Odoo `command` | Exec form: `python3 -m dev_project.inside_docker_app.run_odoo` | | |
| Runtime config | `.odpm/runtime/config.json` exists; `schema_version: 1` | | |
| Debug profile (developer) | `.odpm/runtime/debug-profile.json` exists; `schema_version: 1`; `odpm plan` shows `ide.debug_profile` | | |
| Secrets (optional) | With `.odpm/secrets.json`: `secrets.materialize` in plan; runtime JSON exists; compose has `ODPM_SECRETS_PATH` + `:ro` mount to `/run/odpm/secrets.json` | | |
| Compose env | `ODPM_CONFIG_PATH=/run/odpm/config.json` + read-only mount of runtime JSON | | |
| No legacy placeholders | No `{START_STRING}` / base64 bootstrap | | |
| No default healthcheck | No embedded `healthcheck:` in project compose template | | |
| Stack starts | `docker compose up -d` succeeds | | |
| HTTP | `/web` returns success on configured `ODOO_PORT` | | |

---

## 2C — Database state v1 (4.3+)

On a developer/server project with host-mounted runtime config:

```bash
cd "$ODPM_PROJECT"
odpm database status --skip-start
odpm plan --skip-start
```

| Check | Expected | Result | Date |
|-------|----------|--------|------|
| `database status` | Exit 0; table or JSON with compose fingerprints | | |
| First run (no `last_run.json`) | Adoption on next full `odpm`; file created under `.odpm/database/` | | |
| `odpm plan` | Step `database.drift` present (noop or run) | | |
| Compose mount | `.odpm/database` mounted to `/run/odpm/database` in odoo service | | |
| `database ensure-role` | Creates/updates app role when postgres is up | | |

Docs: [database-state.md](reference/database-state.md).

---

## 2B+ — Plan dry-run (`odpm plan` / `odpm --plan`)

Run on the same migrated project as **2B** after templates are in place:

```bash
cd "$ODPM_PROJECT"
odpm plan --skip-start
odpm plan --plan-format json | jq .
# or: odpm --plan --skip-start  (deprecated alias; logs a warning)
# or: python3 "$ODPM_REPO/odpm.py" plan --skip-start
```

| Check | Expected | Result | Date |
|-------|----------|--------|------|
| Exit code | 0 | | |
| Table header | `Action   Required  ID                    Reason` | | |
| Git branch | `RUN git.materialize` or `SKIP`/`RUN` for `--no-git-update` / `--update-lock` | | |
| Idle project | `NOOP compose.service` and `NOOP compose.generate` when runtime hash matches and root `docker-compose.yml` exists | | |
| Stale runtime | `UPDATE compose.service` with reason `venv_lock_hash changed` after venv/scenario change | | |
| Missing compose | `RUN compose.service` + `UPDATE compose.generate` when root `docker-compose.yml` is absent | | |
| Compose probe | `compose.up` reason includes `without --force-recreate (stack healthy)` or `with --force-recreate (stack missing or unhealthy)` | | |
| `--plan-no-docker` | Warning `Compose stack health was not probed; --force-recreate is unknown`; reason mentions unknown recreate | | |
| `--plan-show-diff` | Section `Planned changes:` with pretty-printed unified diff for runtime config (compose.service path), compose, dockerignore; plan-only CLI flags excluded from comparison | | |
| `--plan-format json` | Valid JSON with `plan_version`, `steps[]` (`outcome`, not `action`), `warnings`, optional `compose_up.force_recreate`, optional `diffs` | | |
| `--plan-strict` | Exit code 1 when any required step is `run` or `update`; 0 when only noop/skip/optional run | | |
| `odpm plan` | Same output and flags as `--plan`; project flags work after subcommand | | |
| Warnings | Lock warnings when applicable; no generic recreate warning when probe runs | | |

Automated analogue (repository tests):

```bash
cd "$ODPM_REPO"
python3 -m unittest tests.test_odpm_plan_smoke tests.test_plan_compose_probe tests.test_plan_diff tests.test_plan_format tests.test_plan_cli -v
```

---

## 2C — Golden path E2E (opt-in integration)

Requires Docker and an **initialized** project at `$ODPM_GOLDEN_PATH_PROJECT` (same as `$ODPM_PROJECT`).

```bash
cd "$ODPM_PROJECT"
docker compose down
export ODPM_GOLDEN_PATH_PROJECT="$ODPM_PROJECT"
export ODPM_RUN_DOCKER_INTEGRATION=1
"$ODPM_REPO/scripts/run_golden_path_test.sh"
```

| Check | Expected | Result | Date |
|-------|----------|--------|------|
| `test_compose_up_serves_web` | PASS; HTTP 200 on `/web` | | |

Optional timeout override: `ODPM_GOLDEN_PATH_TIMEOUT=60` (default; CI job ≤3 min). DB remedi ate is not part of CI — run `ODPM_GOLDEN_PATH_AUTO_REMEDIATE=1 … refresh_golden_path_project.sh` on the runner.

---

## 2D — OCA / nested `odpm.json` (optional)

Run only if you maintain projects with `"use_oca_dependencies": true` and transitive git deps.

**Setup (example):** enable `use_oca_dependencies` in `user_settings.json`; ensure `odpm.json` lists at least one git dependency whose tree includes `oca_dependencies.txt` or nested `odpm.json`.

```bash
cd "$ODPM_PROJECT"
odpm --update-lock --skip-start
odpm --skip-start
odpm
curl -sL -o /dev/null -w '%{http_code}\n' "http://127.0.0.1:${ODOO_PORT:-8069}/web/login"
```

| Check | Expected | Result | Date |
|-------|----------|--------|------|
| `--update-lock` | Writes `.odpm/deps.lock.json` with resolved graph | | |
| `--skip-start` + checkout | Locked SHAs applied; compose regenerated | | |
| Dependency mounts | Git deps appear in compose volumes and runtime `addons_path` | | |
| HTTP | Login page HTTP 200 (or project-appropriate code) | | |

---

## 2E — CI scenario (optional)

Requires `ODPM_SCENARIO=ci` and a project with CI layout / lock file as documented in README.

```bash
export ODPM_SCENARIO=ci
export ODPM_CI_PROJECT="$ODPM_PROJECT"   # optional: prepare project before build
"$ODPM_REPO/scripts/verify_ci_scenario.sh"
```

| Check | Expected | Result | Date |
|-------|----------|--------|------|
| CI image build | `odpm --build-image` succeeds | | |
| Compose up | Stack starts without host Odoo bind-mounts | | |
| HTTP | `/web` returns 200 on configured port | | |

---

## Step 3 — `dev_mode` (developer scenario only)

**Protocol:** `dev_mode` in `user_settings.json` → Odoo `--dev` in compose (not a separate odpm CLI flag). Applied only when `ODPM_SCENARIO=developer`; ignored on `server`/`ci` with a warning. With `reload` or `all`, odpm adds `inotify` to Python requirements.

Back up `user_settings.json` before experiments.

### 3A — Manual spot checks (optional)

After each `dev_mode` change: `odpm --skip-start`, restart stack, check container stays up and HTTP on `/web/login`.

Note: `--dev xml` may surface QWeb errors on some projects (Odoo/project level), not necessarily an odpm failure.

### 3B — Automated matrix

```bash
export ODPM_GOLDEN_PATH_PROJECT="$ODPM_PROJECT"
export ODPM_SCENARIO=developer
cd "$ODPM_PROJECT"
docker compose down
"$ODPM_REPO/scripts/verify_dev_mode_flags.sh"
"$ODPM_REPO/scripts/verify_dev_mode_autoreload.sh"
```

| Check | Expected | Result | Date |
|-------|----------|--------|------|
| Compose matrix | 13 cases PASS (`test_all_dev_mode_flags_compose`) | | |
| Live HTTP matrix | 13 cases PASS (`test_all_dev_mode_flags_live`) | | |
| Autoreload probe | PASS with `dev_mode=all` after auto-`inotify` | | |

Restore `dev_mode` in `user_settings.json` after testing.

**Related tests:** `tests/test_dev_mode.py`, `tests/integration/test_dev_mode_flags.py`, `tests/test_scenario_policy.py`.

---

## Step 4 — Documentation sync

Before release, confirm public docs match behavior:

| Document | Verify |
|----------|--------|
| `CHANGELOG.md` / `CHANGELOG-RU.MD` | 4.0.0 breaking changes, migration, feature list |
| `README.MD` / `README-RU.MD` | Scenarios, `odpm plan`, deps lock, pip install, integration test env vars |
| `goals_ru.md` | Architecture / backlog aligned with 4.0 |
| This checklist | Test count and steps still accurate |

---

## Local notes

Detailed smoke reports (timings, project-specific findings, customer repo names) belong in **local files only**, for example:

- `docs/smoke-local.md` (recommended filename)
- or any path listed in `.gitignore`

Do not commit private project paths, host home directories, or proprietary dependency URLs into the public repository.

---

## 4.5 — Integration matrix (ADR-006)

**Branch:** `4.7.0-dev`. Policy: [contributing/ci.md](contributing/ci.md), [ADR-006](contributing/adr-006-integration-gate-policy.md).

### Required on every PR

| Check | Script / CI job | Expected |
|-------|-----------------|----------|
| compose-smoke (T1) | `./scripts/run_compose_smoke_test.sh` | exit 0 |
| compose-smoke-mailpit | `./scripts/run_compose_smoke_mailpit_test.sh` | exit 0 |
| plugin + hooks E2E | `./scripts/run_compose_smoke_extended_test.sh` | exit 0 |
| http-smoke (T2) | `./scripts/run_http_smoke_test.sh` | Mailpit HTTP 200 |
| unit + contract | `python3 -m unittest discover -s tests -q` | **1283+** OK |

### Weekly (`ci-integration-weekly.yml`)

| Check | Script | Expected |
|-------|--------|----------|
| fixture golden-path `/web` | `./scripts/run_fixture_golden_path_test.sh` | HTTP 200/303 on `/web` |
| CI image build | `ODPM_RUN_DOCKER_INTEGRATION=1 python3 -m unittest tests.integration.test_ci_image_build` | docker build OK |
| deb install smoke | `./scripts/build_deb.sh && ./scripts/smoke_deb_install.sh` | `deb smoke OK` |

### Opt-in full golden-path (T3)

`ODPM_GOLDEN_PATH_PROJECT=$ODPM_PROJECT ./scripts/run_golden_path_test.sh` — self-hosted / nightly / label `run-docker`.

---

## Gate verdict

| Step | Pass? | Sign-off |
|------|-------|----------|
| 2A Unit baseline | | |
| 2B Developer migration | | |
| 2C Golden path (if run) | | |
| 2D OCA (if run) | | |
| 2E CI (if run) | | |
| 3 dev_mode (if run) | | |
| 4 Documentation | | |

**4.0 stable smoke:** all required rows Pass.
