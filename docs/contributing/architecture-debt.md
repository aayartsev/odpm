# Architecture debt (A10 / A4 / A11) — status

**Status:** G/C/E tracks **completed** on branch `4.0-beta`; **4.4 extension hub** (C-8…C-10, manifest v2, plugins) **completed** on `4.4-dev`.  
This document is a **retrospective** for audits and onboarding; new architecture work needs a separate plan.

**Test baseline (2026-06):** `python3 -m unittest discover -s tests -q` → **1000+ OK**, 7 skipped; CI job **`contract`** runs manifest/extension suite without Docker.

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

## A4-2 Config hub slimming (C-7…C-10) — DONE

| Slice | Status | Outcome |
|-------|--------|---------|
| C-7 | **DONE** | `BootstrapState` + property shims; `config.bootstrap`; `bootstrap_phases` internal |
| C-8 | **DONE** | `AddonLayoutState` (`catalogs_of_modules_data`, developing subprojects) |
| C-9 | **DONE** | prepare steps → `host_ctx` (paths, policy, docker_layout reads) |
| C-10 | **DONE** | `ConfigPaths` writes to `docker_layout` slice |

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

## 4.4 Extension API (manifest v2, plugins) — DONE

| Area | Outcome | Docs / tests |
|------|---------|--------------|
| Manifest v2 | dual-read, jsonschema, migrate CLI | `test_manifest_v2_reader`, `test_manifest_migrate` |
| Locks in manifest | **DONE** | dual-source docs, plan warnings, `git.lock_verify` divergence warning |
| Extension registry | pluggy prepare steps, compose fragments | `test_extension_entry_points` |
| Compose fragments | `compose.fragments` prepare step | `test_compose_fragments` |
| Lifecycle hooks | `post_prepare`, `pre_up` | `test_manifest_hooks` |
| Contract CI | `tests.test_manifest_contract` | `.github/workflows/ci.yml` job `contract` |

ADR: [adr-001-extensions-and-manifest-v2.md](adr-001-extensions-and-manifest-v2.md). User docs: [plugins.md](../reference/plugins.md), [manifest-migration.md](../reference/manifest-migration.md).

---

## Remaining micro-debt (not G/C/E)

| Item | Priority | Notes |
|------|----------|-------|
| `Config` facade still central | P2 | C-11a/b slimmed prepare steps; shims remain for bootstrap boundary |
| `DEFAULT_ODPM_VERSION` "3.0" vs `MANIFEST_V1_CONTRACT_LINE` "4.0" | **DONE** | Documented in odpm-json.md; `odpm manifest validate` |
| Env variable refs in `odpm.json` | **DONE (MVP)** | `${VAR}` whitelist — see CHANGELOG 4.3 |
| CI image secrets bake (TD-FEAT-09 Phase B) | **DONE** | `ODPM_BAKE_SECRETS=1` + ADR-002; `test_ci_secrets_smoke` bake cases |
| PyYAML for compose fragments | P3 | Stage-1 stdlib renderer; revisit if external YAML fragments needed |

---

## C-11 prepare boundary (4.4 debt closure)

New prepare/plan evaluation code should prefer:

| Read path | Use |
|-----------|-----|
| Paths, policy, CLI flags, settings slices | `PrepareContext.host_ctx` (`HostProjectContext`) |
| Extension compose/prepare plugins | `PrepareContext.extension_host()` |
| Git materialize / ensure present | `PrepareContext.git_repos` (`GitRepoCoordinator`) |
| Lock apply / verify / collect | `DepsLockManager.apply_pinned_locks()` and related helpers |
| Bootstrap-only mutations | `PrepareContext.config` (compose service build, drift collection, lock manager ctor) |

`prepare/steps_*.py` must not reference `ctx.config` directly (enforced by `tests/test_prepare_config_coupling.py`).

---

## Next architecture work

See [goals_ru.md](../../goals_ru.md) horizon items not covered by 4.4 (full Doodba-style hook surface, mandatory golden-path on every PR, etc.).
