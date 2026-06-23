# ADR-009: Compose service patch vs replace (4.6)

**Status:** accepted (4.6.0-dev)  
**Date:** 2026-06-23

## Context

Manifest v2 `services` and plugin `compose_services()` merged via `merge_services()` **replaced** whole services by name. That made it impossible to add env vars or ports to built-in `odoo` / `db` without redefining the entire service block.

Phase D2 (debt closure 4.6) separates **sidecar services** from **patches** to generated stack services.

## Decision

### Manifest fields

| Field | Purpose | Targets |
|-------|---------|---------|
| `services` | Declarative **extra** compose services (Mailpit, Redis, …) | New service names only |
| `service_patches` | Partial updates to **built-in** services | `odoo`, postgres service name (`db` by default), … |

Reserved names in `services`: **`odoo`**, **`db`**, **`postgres`** → `ConfigError` at load; use `service_patches` instead.

### Patch merge (`merge_services_with_patches`)

- **Scalars** (`image`, `user`, `restart`, …): patch value wins.
- **Dict** (`environment` object in manifest): keys merged.
- **Lists** (`ports`, `volumes`, `depends_on`, `command`, `entrypoint`, list `environment`): patch **replaces** the entire list when provided.
- **List + dict `environment`**: when base uses `environment: ["KEY=value", …]` and patch uses `environment: {"KEY": "value"}`, new keys are **appended** as `KEY=value` lines; existing keys are not rewritten in 4.6.0.

### `command` / `entrypoint` (D2-7)

- Allowed on **extra** `services.*` and in `service_patches` (exec form only: JSON array of strings).
- Shell-form string `command` — **deferred**.
- Built-in `odoo` start command remains owned by `ComposeServiceBuilder` / `StartCommand`; patch may override via `service_patches.odoo.command` when explicitly needed.

### Plugin `compose_services()`

- Same `composeService` keys as manifest `services` (including `command` / `entrypoint`).
- Must not declare reserved built-in names (`odoo`, `db`, `postgres`).
- Plugin vs manifest same name → plugin spec **replaces** manifest (unchanged `merge_services`).

### Plan integration

- `odpm plan` shows `compose.patch.<name>` for each `service_patches` entry (preview only; applied at `compose.generate`).

## Consequences

- `dev_project/yaml/engine.py`: `merge_services_with_patches`.
- Schema: `odpm_manifest.v2.json` — `service_patches`, `command`, `entrypoint`.
- Tests: `test_yaml_engine.py`, `test_compose_fragments.py`, `test_manifest_v2_reader.py`.
- Docs: `plugins.md`, `manifest-migration.md`.

## Non-goals (4.6.0)

- `docker-compose.override.yml` merge (D5-3).
- JSON Schema validation of final compose output (D5-1).
- **Nested dependency `services` merge** — implemented in 4.6 D4: transitive v2 `odpm.json` `services` / `service_patches` inherit when `use_oca_dependencies` resolves nested fragments; host manifest wins on conflict ([ADR-004](adr-004-plugin-api-stability.md)).
