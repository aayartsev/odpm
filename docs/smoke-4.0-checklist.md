# Smoke checklist: odpm 4.0 stable gate

Manual verification protocol before tagging **4.0.0**. Fill in **Result** and **Date** when you run each step on your machine. Do not commit paths to private customer projects — keep detailed notes in a local file (see [Local notes](#local-notes)).

## Variables

Set these in your shell before running project-scoped steps:

```bash
export ODPM_REPO=/path/to/odoo_dev_project   # clone of this repository
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

Run from **`$ODPM_REPO`**:

```bash
cd "$ODPM_REPO"
python3 -m unittest discover -s tests -p "test_*.py"
```

| Check | Expected | Result | Date |
|-------|----------|--------|------|
| Test suite | All tests OK; 5 skipped (opt-in Docker integration unless `ODPM_RUN_DOCKER_INTEGRATION=1`) | | |
| Test count | Matches current baseline (see CHANGELOG; re-run after adding tests) | | |

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
| Compose env | `ODPM_CONFIG_PATH=/run/odpm/config.json` + read-only mount of runtime JSON | | |
| No legacy placeholders | No `{START_STRING}` / base64 bootstrap | | |
| No default healthcheck | No embedded `healthcheck:` in project compose template | | |
| Stack starts | `docker compose up -d` succeeds | | |
| HTTP | `/web` returns success on configured `ODOO_PORT` | | |

---

## 2B+ — Plan dry-run (`odpm --plan`)

Run on the same migrated project as **2B** after templates are in place:

```bash
cd "$ODPM_PROJECT"
odpm --plan --skip-start
# or: python3 "$ODPM_REPO/odpm.py" --plan --skip-start
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
| Warnings | Lock warnings when applicable; no generic recreate warning when probe runs | | |

Automated analogue (repository tests):

```bash
cd "$ODPM_REPO"
python3 -m unittest tests.test_odpm_plan_smoke tests.test_plan_compose_probe -v
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

Optional timeout: `ODPM_GOLDEN_PATH_TIMEOUT=600`.

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
| `README.MD` / `README-RU.MD` | Scenarios, `--plan`, deps lock, pip install, integration test env vars |
| `goals_ru.md` | Architecture / backlog aligned with 4.0 |
| This checklist | Test count and steps still accurate |

---

## Local notes

Detailed smoke reports (timings, project-specific findings, customer repo names) belong in **local files only**, for example:

- `docs/smoke-local.md` (recommended filename)
- or any path listed in `.gitignore`

Do not commit private project paths, host home directories, or proprietary dependency URLs into the public repository.

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
