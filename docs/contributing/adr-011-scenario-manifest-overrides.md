# ADR-011: Scenario-specific manifest overrides (4.7)

**Status:** proposed (4.7.0-dev)  
**Date:** 2026-06-25

## Context

`ODPM_SCENARIO` (`developer` | `server` | `ci`) selects **built-in host policy** via `ScenarioPolicy` ([ADR-007](adr-007-base-image-profiles.md)): base image profile, debugpy, postgres bind address, `dev_mode`, runtime mounts, and similar. That policy is **code**, not manifest.

Manifest v2 ([ADR-001](adr-001-extensions-and-manifest-v2.md)) exposes user-controlled stack fields at the top level:

| Field | Role (4.6) |
|-------|------------|
| `odoo_conf` | Team Odoo option overrides (reserved keys enforced) |
| `services` | Extra compose sidecars ([ADR-009](adr-009-compose-service-patch.md)) |
| `service_patches` | Partial patches to built-in `odoo` / postgres service |
| `requirements` | Extra Python packages for the project venv |

These fields are **shared across all scenarios**. Teams that need different `odoo.conf`, compose sidecars, or Python extras on laptop vs server today rely on `${VAR}` in manifest plus **per-host** `.env`.

Goal: **one `odpm.json` in git**, scenario from project `.env`, optional **per-scenario overlays** without forking the project or replacing `ScenarioPolicy`.

## Decision

### Versioning

- **Manifest schema stays v2** (`manifest_schema: 2`). Backward-compatible extension, not v3.
- Manifests that use `scenarios` SHOULD set `requires_odpm` to **4.7.0** or newer.
- **`scenarios` on manifest v1** → `ConfigError` at validate/load with migrate-to-v2 hint.

### New field: `scenarios`

Optional object on manifest v2 root. Keys: **`developer`**, **`server`**, **`ci`** only (`additionalProperties: false`).

Each value (`scenarioOverlay`) may include any subset of:

| Field | Schema reuse |
|-------|----------------|
| `odoo_conf` | Same shape as top-level `odoo_conf` |
| `services` | `#/$defs/composeService` |
| `service_patches` | `#/$defs/composeServicePatch` |
| `requirements` | Same as top-level `requirements` (string array) |

### Effective slice semantics

Host helper: `resolve_effective_manifest_slice(raw, active_scenario) -> ScenarioManifestSlice`.

| Mode | Condition | Effective slice |
|------|-----------|-----------------|
| **Legacy** | `scenarios` key **absent** | Top-level `odoo_conf` / `services` / `service_patches` / `requirements` only |
| **Multi** | `scenarios` key **present** (including `{}`) | Deep merge: top-level base + `scenarios[active_scenario]` overlay |

`active_scenario` comes from `ODPM_SCENARIO` in `.env` (unchanged). Unknown scenario → `developer`.

### Merge rules

| Field | Merge |
|-------|-------|
| `odoo_conf` | Deep merge by section (`merge_odoo_conf_sections`) |
| `services` | `merge_services` — overlay replaces whole service by name |
| `service_patches` | `merge_service_patch_maps` per ADR-009 |
| `requirements` | **Append + dedupe** (base order, then overlay; first occurrence wins) |

`ScenarioPolicy` (debugpy, stubs, baked venv, …) still applies **after** manifest effective requirements at bootstrap (PR2).

### Validation (`odpm manifest validate`)

1. JSON Schema (v2) including `scenarios`.
2. **v1 + `scenarios`** → reject.
3. **Legacy:** validate top-level `odoo_conf` + `services` once.
4. **Multi:** validate each **declared** `scenarios.*` subtree; then for **each** of `developer`, `server`, `ci` compute `resolve_effective_manifest_slice(raw, S)` and validate effective `odoo_conf` + `services` (reserved keys, compose policy).

`${VAR}` expansion in validate is **deferred** to PR2 (runtime wire with `EnvResolver`); PR1 tests use raw JSON.

### Runtime wire (deferred)

| Phase | Scope |
|-------|--------|
| **4.7 PR1 (A1)** | `scenario_overrides.py`, schema, `validate` only — **no** `load_manifest` / `ManifestView` change |
| **4.7 PR2 (A2)** | Effective slice → `odoo_conf`, `requirements_txt` pipeline |
| **4.7 PR3 (A3)** | Effective slice → compose fragments / plan |

Compose **service name prefix** from `.env` is a separate track (4.7 plan track B); logical names `db` / `odoo` in manifest are unchanged.

## Consequences

- **New:** `dev_project/manifest/scenario_overrides.py`, `ScenarioManifestSlice`.
- **Schema:** `odpm_manifest.v2.json` — `scenarios`, `$defs.scenarioOverlay`.
- **Validate:** `dev_project/manifest/commands.py` — `validate_scenario_manifest`.
- **Tests:** `tests/test_manifest_scenario_overrides.py`.

## References

- [ADR-001](adr-001-extensions-and-manifest-v2.md) — manifest v2 axes
- [ADR-009](adr-009-compose-service-patch.md) — patch merge
- Plan: `.cursor/plans/4.7_scenarios_compose_prefix_9b4acf8a.plan.md`
