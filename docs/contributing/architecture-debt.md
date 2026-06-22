# Architecture debt (A10 / A4 / A11) — status

**Status:** G/C/E tracks **completed** on branch `4.0-beta` (see CHANGELOG `[Unreleased]` refactor bullets).  
This document is a **retrospective** for audits and onboarding; new architecture work needs a separate plan.

**Test baseline (2026-06):** `python3 -m unittest discover -s tests -q` → **1221+ OK**, 8 skipped.

---

## 4.4 debt remainder (4.4.3) — CLOSED

| Phase | Outcome | Notes |
|-------|---------|-------|
| **C-12** plan boundary | **DONE** | `locks_preview` / compose preview evaluate via `host_ctx` + `PrepareContext` ports; `tests/test_plan_config_coupling.py` |
| **L2** locks dual-write | **DONE** | opt-in `--sync-manifest-locks` with `--update-lock` (developer, manifest v2) |
| **H** hygiene | **DONE** | lock source log in `enter_apply_mode`; i18n divergence warnings; contract suite + smoke/ci docs |

**Open horizon (4.5+):** full `Config` facade removal (C-11/C-12 incremental only); PyYAML compose engine; mandatory golden-path on every PR — see [goals_ru.md](../../goals_ru.md).

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

## A4-2 Config hub slimming (C-7…) — IN PROGRESS

| Slice | Status | Outcome |
|-------|--------|---------|
| C-7 | **DONE** | `BootstrapState` + property shims; `config.bootstrap`; `bootstrap_phases` internal |
| C-8 | backlog | `AddonLayoutState` (`catalogs_of_modules_data`, …) |
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
| `Config` facade still central | P2 (4.5+) | C-11/C-12/L2 slimmed prepare/plan evaluate; full removal deferred |
| `DEFAULT_ODPM_VERSION` "3.0" vs `ODPM_VERSION` "4.0" | P2 | Fallback for legacy `odpm.json` |
| Plugin/hook API | backlog | `goals_ru.md` vision only |
| Env variable refs in `odpm.json` | backlog | `todo.md` |
| CI image secrets bake (TD-FEAT-09 Phase B) | P1 | Separate from developer `--secrets-file` MVP |

---

## Next architecture work

When starting a **new** track, add a new plan document rather than reopening G/C/E slices.

Maintainers using Cursor: local workflow rule `.cursor/rules/architecture-debt-workflow.mdc` (not in git; `.cursor/` is gitignored).
