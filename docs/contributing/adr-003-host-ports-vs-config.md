# ADR-003: Host ports vs Config bootstrap

## Status

Accepted (4.5 architecture track, slice C-14). **Amended** for 4.6 debt closure slice D3 (C-15…C-18).

## Context

`Config` remains the **bootstrap hub**: it loads `user_settings.json` / `odpm.json`, builds typed slices (`UserSettingsState`, `DockerLayoutState`, …), wires git coordinators, and runs materialize side effects (`generate_odoo_conf_docker_data`, `ComposeServiceBuilder`, git clone).

After C-8/C-12/C-13, most **read-only** plan/prepare evaluation uses `HostProjectContext` and `PrepareContext` helpers instead of scattered `config.` access. Pipeline thinning (first version) also removed the public bare `Config` from `OdpmPipeline`, `RuntimeCoordinator`, `SystemChecker`, and host `*/commands.py`: callers take `PipelinePorts` / `RuntimePorts` / `BootstrapHandle`.

## Decision

Introduce frozen **host ports** at the pipeline boundary:

| Port | Role | Typical consumers |
|------|------|-------------------|
| `BootstrapHandle` | Mutable bootstrap hub: `config`, `git_repos`, `env_resolver`, `odoo_conf`, `pd_manager`, lock manager factory, venv lock hash (see also [ADR-030](adr-030-config-as-assembler.md)) | execute steps, drift detection at bootstrap boundary |
| `PlanPorts` | `host_ctx` + CLI args + bootstrap handle | plan diff/format, prepare evaluate, lock warnings |
| `ComposePorts` | `host_ctx` + `CreateProjectEnvironment` + bootstrap | compose generator, plan compose preview |
| `RuntimePorts` | `host_ctx` + args + project env + bootstrap | runtime plan steps, `RuntimeCoordinator` |
| `PipelinePorts` | Bundle of the three; built once in `OdpmPipeline.setup()` | `OdpmPlanner`, `ProjectMaterializer`, `print_plan`, host `database` / `manifest` / `modules` / `run` commands |

Module: `dev_project/host/ports.py`.

### Rules

1. **Pipeline entrypoints** (`OdpmPlanner.build`, `ProjectMaterializer.run`, `print_plan`, host `run_*_command`) take `PipelinePorts`, not bare `Config`. `OdpmPipeline` has no public `.config` after `setup()` — only `ports` / `project_environment` / `system_checker`.
2. **Plan/prepare/runtime evaluate** reads paths and policy via `host_ctx` (or port fields), not `config.project_dir` / `config.policy` shims. `RuntimeCoordinator` takes `RuntimePorts`; `SystemChecker` takes `BootstrapHandle`.
3. **Materialize** (execute steps, `ComposeServiceBuilder`, git) uses `ports.bootstrap` — `config`, `git_repos`, `env_resolver`, `odoo_conf`, `pd_manager`, `new_lock_manager()`, `compute_venv_lock_hash()`. Plan/prepare **evaluate** must not read `ctx.config`; use `host_ctx`, `PrepareContext` helpers, or `ports.bootstrap` only where drift/compose builder still need raw `config`.
4. **Manifest read model** (`manifest_view`, `repo_odpm_json`) is copied into `HostProjectContext` at port construction; evaluate paths use `host_ctx.manifest_view` / `ctx.manifest_view`, not `config.bootstrap.manifest_view`.
5. **Tests** may call `ports_from_config(config, …)` when constructing ports without a full pipeline.

### Config property shims (deprecated for new callers)

`Config` exposes slice fields via `bind_slice_properties` and runtime fields via `ConfigRuntimeFacadeMixin`. New code should prefer:

| Instead of | Use |
|------------|-----|
| `config.project_dir`, `config.policy`, … | `host_ctx.project_dir`, `host_ctx.policy`, … |
| `config.docker_compose_command` | `host_ctx.docker_compose_command` |
| `config.catalogs_of_modules_data` | `host_ctx.addon_layout.catalogs_of_modules_data` |
| `config.arguments` in plan/prepare | `PlanPorts.args` / `PrepareContext.args` |
| `config.bootstrap.manifest_view` | `host_ctx.manifest_view` / `ctx.manifest_view` |
| `config._git_repos` / `config.compute_venv_lock_hash()` | `ports.bootstrap.git_repos` / `ports.bootstrap.compute_venv_lock_hash()` |
| `config.env_resolver` / `config._odoo_conf` / `config.pd_manager` | `ports.bootstrap.env_resolver` / `odoo_conf` / `pd_manager` |
| Passing `Config` into planner/materializer | `PipelinePorts` |

Full shim inventory: `CONFIG_PROPERTY_SHIMS` in `dev_project/config/state.py`.

## Consequences

- `OdpmPipeline.ports` is set in `setup()`; plan, prepare, runtime coordinator, system checks, and host tooling no longer expose raw `Config` on their public constructors.
- `PrepareContext` holds `PipelinePorts`; execute-only helpers that still need a snapshot use `ports.bootstrap.config` (no `PrepareContext.config` alias).
- `ExtensionHostContext.from_host()` builds plugin views from `HostProjectContext` without touching `Config`.
- `ComposePreviewPort` on `PrepareContext.compose_preview` is the evaluate-time compose preview surface (bootstrap config for disk cache only).
- Removing the `Config` class is **out of scope** for 4.5.0; target is ~50% fewer direct `config.` reads in plan/prepare/runtime vs 4.4.3 (D3 narrows bootstrap access further).
- Contract guards: `tests/test_plan_config_coupling.py`, `tests/test_prepare_config_coupling.py`, `tests/test_addon_layout_ports.py`, `tests/test_pipeline_ports.py`, `tests/test_host_context.py`.

### 4.6 amendment (D3 / C-15…C-18)

| Slice | Outcome |
|-------|---------|
| C-15 | Coupling guards extended to manifest preview modules (`patches_preview`, `fragments_preview`, `hooks_preview`, `database_preview` host entry); `bootstrap.config` allowed on handle boundary |
| C-16 | `BootstrapHandle` exposes `git_repos`, `new_lock_manager()`, `compute_venv_lock_hash()`; `CONFIG_PROPERTY_SHIMS` documents `manifest_view` → `host_ctx` |
| C-17 | Prepare evaluate uses `host_ctx` for git lock paths; execute uses `ports.bootstrap` for git/lock managers |
| C-18 | This amendment |

### Host API / project_env thinning (H1 + E1)

| Slice | Outcome |
|-------|---------|
| H1 | Public database status / role / adopt / blocking-drift APIs and module-diff take `BootstrapHandle`; `detect_database_drift_for_config` removed; plan warnings use `collect_database_drift_warnings_for_host` only; `compute_module_diff_for_handle` replaces `*_for_config` |
| E1 | `project_env` services (`ProjectTemplates`, `ProjectLinks`, `VolumeMapper`, image/IDE builders and related services) no longer expose a public `.config` property; raw snapshot remains `env.bootstrap.config` inside methods only |

### Env bootstrap thinning (M1–M3)

| Slice | Outcome |
|-------|---------|
| M1 | `DependencyMaterializer` takes `BootstrapHandle` (no public `.config`); Links passes `env.bootstrap` |
| M2 | `ProjectLinks` / `VolumeMapper` read paths and settings slices via `env.host_ctx`; git project objects and Config methods stay on `env.bootstrap.config`; `SymlinkManager(self.env.bootstrap, …)` |
| M3 | `CiImageBuilder` / `CiImageBuildService` same read rule; `run_layered_build(..., host_ctx.arguments)`; bake mutations (`_env_resolver`, secrets, runtime write) keep a local snapshot |

## References

- [ADR-001](adr-001-extensions-and-manifest-v2.md) — manifest vs manager version axes
- [ADR-030](adr-030-config-as-assembler.md) — Config as assembler; zone map in [config-zones.md](config-zones.md)
