# Architecture debt (A10 / A4 / A11) — status

**Status:** G/C/E tracks **completed** on branch `4.0-beta` (see CHANGELOG `[Unreleased]` refactor bullets).  
This document is a **retrospective** for audits and onboarding; new architecture work needs a separate plan.

**Test baseline (2026-06-23):** `python3 -m unittest discover -s tests -q` → **1381** OK, 24 skipped.

**Active dev branch:** `4.6.0-dev` (debt closure 4.6). Stable line: **v4.5.0** (`LATEST_STABLE_RELEASE`); roadmap 4.5 **RELEASED**.

---

## 4.4 debt remainder (4.4.3) — CLOSED

| Phase | Outcome | Notes |
|-------|---------|-------|
| **C-12** plan boundary | **DONE** | `locks_preview` / compose preview evaluate via `host_ctx` + `PrepareContext` ports; `tests/test_plan_config_coupling.py` |
| **L2** locks dual-write | **DONE** | opt-in `--sync-manifest-locks` with `--update-lock` (developer, manifest v2) |
| **H** hygiene | **DONE** | lock source log in `enter_apply_mode`; i18n divergence warnings; contract suite + smoke/ci docs |

**Open horizon (4.5):** см. секцию **4.5 track** ниже.

---

## 4.5 track (A / P / Y / I / L / S) — RELEASED stable v4.5.0

Старт после stable **v4.4.3** (2026-06-22). Не reopen G/C/E slices.

| Track | ID | Статус | Суть |
|-------|-----|--------|------|
| Architecture | **A** | **DONE** (4.5) | C-8/C-13/C-14 + A4 micro-debt (`user_env` split, `v1_contract` warn) |
| Plugins | **P** | **DONE** (4.5) | API 1.0, ADR-004, `post_clone`, plan hooks/fragments, local plugins |
| YAML | **Y** | **DONE** (4.5) | `dev_project/yaml/`, structured `ComposeGenerator`, ADR-005 |
| Integration | **I** | **DONE** (4.5 I1–I4) | ADR-006; T1+T2 PR gates; weekly I2 matrix; I3 flakes/artifacts |
| i18n | **L** | **DONE** (4.5 L1–L4) | ADR-008; `check_i18n_catalog` CI gate; ~290 host msgids incl. `plan_msg` |
| Images | **S** | **DONE** (4.5) | Scenario base Dockerfile profiles (ADR-007) |

**ADR backlog (4.5):** ADR-003 Host ports **done**; ADR-004 Plugin API **done**; ADR-005 YAML engine **done**; ADR-006 Integration gate **done** (I1–I4); ADR-008 i18n host/container **done** (L); ADR-007 Base image profiles **done** (S).

**R0 infra (4.6.0-dev):** CI workflows `ci.yml`, `ci-docker.yml`, `docs.yml` target `4.6.0-dev`; branch protection — lint, unit, contract, **i18n**, compose-smoke, http-smoke.

---

## 4.6 debt track (D1–D5) — IN PROGRESS

Старт после stable **v4.5.0** и R0 на `4.6.0-dev`. План: `.cursor/plans/debt_closure_4.5-4.6_a59fde99.plan.md`. Единый релиз **v4.6.0 stable** (без v4.5.1).

| Track | ID | Статус | Суть |
|-------|-----|--------|------|
| Ops / docs | **D1** | **DONE** | Pages post-deploy verify (`verify_pages_deploy.sh`); `services_ru` redirect; roadmap/plan hygiene; секция 4.6 track |
| Compose | **D2** | **DONE** | ADR-009, `service_patches`, `merge_services_with_patches`, manifest `command` |
| Config | **D3** | **DONE** | C-15…C-18: narrowed `BootstrapHandle`, `manifest_view` on `host_ctx`, coupling guards, ADR-003 amendment |
| Plugins | **D4** | **DONE** | API 1.1, load-time version check, `compose_service_patches`, nested dep compose inherit, sample_plugin patch |
| YAML | **D5** | **DONE** | Y3 compose validation + golden snapshots per scenario |
| CI-INF | — | pending | runner runbook, deploy-pages bump, timeout docs |

**ADR backlog (4.6):** ADR-009 compose service patch **done** (D2); ADR-003 amendment **done** (D3); ADR-004 plugin 1.1 **done** (D4); ADR-005 Y3 compose validation **done** (D5).

---

## A10 Git (G-1…G-5) — DONE

| Slice | Outcome | Modules |
|-------|---------|---------|
| G-1 | `GitRunner` extracted | `dev_project/git/runner.py` |
| G-2 | `RepoCloneService` extracted | `dev_project/git/clone.py` |
| G-3 | `CheckoutService` extracted | `dev_project/git/checkout.py` |
| G-4 | `BuildDateResolver` extracted | `dev_project/git/build_date.py` |
| G-5 | `GitOperations` removed; `HandleOdooProjectLink` composes services | `dev_project/git/link.py` |

**KPI:** `dev_project/git/operations.py` absent; public `HandleOdooProjectLink` API stable; tests in `test_git_*`.

---

## A4 Config (C-1…C-6) — DONE

| Slice | Outcome | Modules |
|-------|---------|---------|
| C-1 | Manifest readers extracted | `config/manifests/` |
| C-2 | Defaults factory extracted | `config/defaults/factory.py` |
| C-3 | Deprecated handler extracted | `config/artifacts/deprecated.py` |
| C-4 | Transforms extracted | `config/transforms/` |
| C-5 | `ConfigBootstrapContext` replaces loader facade | `config/bootstrap_context.py` |
| C-6 | Paths, OdooConf, GitRepoCoordinator wired in context | `config/bootstrap_phases.py`, `bootstrap.py` <100 LOC |

**KPI:** `dev_project/config/loader.py` absent; `config._loader` mocks removed from tests; bootstrap phases testable.

---

## A4-2 Config hub slimming (C-7…A4) — DONE (4.5)

| Slice | Status | Outcome |
|-------|--------|---------|
| C-7 | **DONE** | `BootstrapState` + property shims; `config.bootstrap`; `bootstrap_phases` internal |
| C-8 | **DONE** (4.5) | addon catalogs via `host_ctx.addon_layout`; `tests/test_addon_layout_ports.py` |
| C-13 | **DONE** (4.5) | plan diff/format + compose runtime via `host_ctx`; lock helpers via `manifest_view`; `tests/test_plan_config_coupling.py` |
| C-14 | **DONE** (4.5) | ADR-003 `PipelinePorts`; `OdpmPipeline.setup()` wires ports; materializer/planner entrypoints; `CONFIG_PROPERTY_SHIMS`; `tests/test_pipeline_ports.py` |
| A4 | **DONE** (4.5) | `user_env` split; `manifest/v1_contract.py` deprecation warn; baseline **1273** tests |
| C-9 | **DONE** (C-11) | prepare steps → `host_ctx` |
| C-10 | **DONE** (4.4) | `ConfigPaths` writes to `docker_layout` |
| C-12 | **DONE** (4.4.3) | plan preview evaluate boundary; see debt remainder table above |

**C-7 KPI:** bootstrap-only fields no longer scattered on `Config.__dict__`; callers unchanged via shims; `developing_project` link on `bootstrap`, URL string on `UserSettingsState`.

---

## A11 Env (E-1…E-6) — DONE

| Slice | Outcome | Modules |
|-------|---------|---------|
| E-1 | `PlatformSourcesService` | `project_env/services/platform_sources.py` |
| E-2 | `VscodeConfigurator` | `project_env/services/vscode_configurator.py` |
| E-3 | `CiImageBuildService` (lazy import) | `project_env/services/ci_image_build.py` |
| E-4 | `BaseImageService` | `project_env/services/docker_base_image.py` |
| E-5 | `CreateProjectEnvironment` slimmed (~50 LOC) | `project_env/environment.py` |
| E-6 | `RuntimeCoordinator` owns post-prepare runtime | `runtime_coordinator.py`, `odpm_pipeline.py` |

**KPI:** runtime delegates removed from `environment.py`; `OdpmPipeline` orchestration thin.

---

## Remaining micro-debt (not G/C/E)

| Item | Priority | Notes |
|------|----------|-------|
| `Config` facade still central | P1 (4.5+) | C-11…C-14 slimmed plan/prepare/runtime; bootstrap via `ports.bootstrap.config` |
| `DEFAULT_ODPM_VERSION` "3.0" vs `ODPM_VERSION` | **DONE** (4.5 A4) | `manifest/v1_contract.py` warns when `odpm_version` missing; v1 compat unchanged |
| `host/user_env.py` monolith | **DONE** (4.5 A4) | `user_env_parse.py` + `user_env_wizard.py`; facade `user_env.py` |
| Plugin/hook API | **DONE** (4.5 P) | `EXTENSION_API_VERSION` 1.0; `post_clone`; local `.odpm/plugins/`; plan `hooks.*` / `compose.fragment.*` |
| Env variable refs in `odpm.json` | **DONE** | `${VAR}` whitelist documented; `todo.md` closed |
| CI image secrets bake (TD-FEAT-09 Phase B) | **DONE** (4.4) | [ADR-002](adr-002-ci-secrets-bake.md); `ODPM_BAKE_SECRETS=1`; `test_ci_secrets_smoke` |

---

## Next architecture work

When starting a **new** track, add a new plan document rather than reopening G/C/E slices.

Maintainers using Cursor: local workflow rule `.cursor/rules/architecture-debt-workflow.mdc` (not in git; `.cursor/` is gitignored).
