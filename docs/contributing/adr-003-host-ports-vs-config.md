# ADR-003: Host ports vs Config bootstrap

## Status

Accepted (4.5 architecture track, slice C-14).

## Context

`Config` remains the **bootstrap hub**: it loads `user_settings.json` / `odpm.json`, builds typed slices (`UserSettingsState`, `DockerLayoutState`, …), wires git coordinators, and runs materialize side effects (`generate_odoo_conf_docker_data`, `ComposeServiceBuilder`, git clone).

After C-8/C-12/C-13, most **read-only** plan/prepare evaluation uses `HostProjectContext` and `PrepareContext` helpers instead of scattered `config.` access. Callers still received a bare `Config` from `OdpmPipeline.setup()` and passed it into `OdpmPlanner` / `ProjectMaterializer`.

## Decision

Introduce frozen **host ports** at the pipeline boundary:

| Port | Role | Typical consumers |
|------|------|-------------------|
| `BootstrapHandle` | Mutable `Config` for materialize/bootstrap only | git steps, odoo.conf, compose service build |
| `PlanPorts` | `host_ctx` + CLI args + bootstrap handle | plan diff/format, prepare evaluate, lock warnings |
| `ComposePorts` | `host_ctx` + `CreateProjectEnvironment` + bootstrap | compose generator, plan compose preview |
| `RuntimePorts` | `host_ctx` + args + project env + bootstrap | runtime plan steps, `RuntimeCoordinator` |
| `PipelinePorts` | Bundle of the three; built once in `OdpmPipeline.setup()` | `OdpmPlanner`, `ProjectMaterializer`, `print_plan` |

Module: `dev_project/host/ports.py`.

### Rules

1. **Pipeline entrypoints** (`OdpmPlanner.build`, `ProjectMaterializer.run`, `print_plan`) take `PipelinePorts`, not bare `Config`.
2. **Plan/prepare/runtime evaluate** reads paths and policy via `host_ctx` (or port fields), not `config.project_dir` / `config.policy` shims.
3. **Materialize** (execute steps, `ComposeServiceBuilder`, git) uses `ports.bootstrap.config` — the only supported path to mutating bootstrap state.
4. **Tests** may call `ports_from_config(config, …)` when constructing ports without a full pipeline.

### Config property shims (deprecated for new callers)

`Config` exposes slice fields via `bind_slice_properties` and runtime fields via `ConfigRuntimeFacadeMixin`. New code should prefer:

| Instead of | Use |
|------------|-----|
| `config.project_dir`, `config.policy`, … | `host_ctx.project_dir`, `host_ctx.policy`, … |
| `config.docker_compose_command` | `host_ctx.docker_compose_command` |
| `config.catalogs_of_modules_data` | `host_ctx.addon_layout.catalogs_of_modules_data` |
| `config.arguments` in plan/prepare | `PlanPorts.args` / `PrepareContext.args` |
| Passing `Config` into planner/materializer | `PipelinePorts` |

Full shim inventory: `CONFIG_PROPERTY_SHIMS` in `dev_project/config/state.py`.

## Consequences

- `OdpmPipeline.ports` is set in `setup()`; plan and prepare orchestration no longer thread raw `Config` through public APIs.
- `PrepareContext` holds `PipelinePorts`; `ctx.config` remains a property alias to `ctx.ports.bootstrap.config` for execute steps until further thinning.
- Removing the `Config` class is **out of scope** for 4.5.0; target is ~50% fewer direct `config.` reads in plan/prepare/runtime vs 4.4.3.
- Contract guards: `tests/test_plan_config_coupling.py`, `tests/test_prepare_config_coupling.py`, `tests/test_addon_layout_ports.py`, `tests/test_pipeline_ports.py`.

## References

- [architecture-debt.md](architecture-debt.md) — C-8, C-12, C-13, C-14
- [ADR-001](adr-001-extensions-and-manifest-v2.md) — manifest vs manager version axes
