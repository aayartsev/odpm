# ADR-003: Host ports vs Config bootstrap

## Status

Accepted (4.5 architecture track, slice C-14). **Amended** for 4.6 debt closure slice D3 (C-15…C-18).

## Context

`Config` remains the **bootstrap hub**: it loads `user_settings.json` / `odpm.json`, builds typed slices (`UserSettingsState`, `DockerLayoutState`, …), wires git coordinators, and runs materialize side effects (`generate_odoo_conf_docker_data`, `ComposeServiceBuilder`, git clone).

After C-8/C-12/C-13, most **read-only** plan/prepare evaluation uses `HostProjectContext` and `PrepareContext` helpers instead of scattered `config.` access. Callers still received a bare `Config` from `OdpmPipeline.setup()` and passed it into `OdpmPlanner` / `ProjectMaterializer`.

## Decision

Introduce frozen **host ports** at the pipeline boundary:

| Port | Role | Typical consumers |
|------|------|-------------------|
| `BootstrapHandle` | Mutable bootstrap hub: `config`, `git_repos`, lock manager factory, venv lock hash | execute steps, drift detection at bootstrap boundary |
| `PlanPorts` | `host_ctx` + CLI args + bootstrap handle | plan diff/format, prepare evaluate, lock warnings |
| `ComposePorts` | `host_ctx` + `CreateProjectEnvironment` + bootstrap | compose generator, plan compose preview |
| `RuntimePorts` | `host_ctx` + args + project env + bootstrap | runtime plan steps, `RuntimeCoordinator` |
| `PipelinePorts` | Bundle of the three; built once in `OdpmPipeline.setup()` | `OdpmPlanner`, `ProjectMaterializer`, `print_plan` |

Module: `dev_project/host/ports.py`.

### Rules

1. **Pipeline entrypoints** (`OdpmPlanner.build`, `ProjectMaterializer.run`, `print_plan`) take `PipelinePorts`, not bare `Config`.
2. **Plan/prepare/runtime evaluate** reads paths and policy via `host_ctx` (or port fields), not `config.project_dir` / `config.policy` shims.
3. **Materialize** (execute steps, `ComposeServiceBuilder`, git) uses `ports.bootstrap` — `config`, `git_repos`, `new_lock_manager()`, `compute_venv_lock_hash()`. Plan/prepare **evaluate** must not read `ctx.config`; use `host_ctx`, `PrepareContext` helpers, or `ports.bootstrap` only where drift/lock still needs bootstrap state.
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
| Passing `Config` into planner/materializer | `PipelinePorts` |

Full shim inventory: `CONFIG_PROPERTY_SHIMS` in `dev_project/config/state.py`.

## Consequences

- `OdpmPipeline.ports` is set in `setup()`; plan and prepare orchestration no longer thread raw `Config` through public APIs.
- `PrepareContext` holds `PipelinePorts`; `ctx.config` remains a property alias to `ctx.ports.bootstrap.config` for execute-only paths until D4+ thinning.
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

## References

- [ADR-001](adr-001-extensions-and-manifest-v2.md) — manifest vs manager version axes
