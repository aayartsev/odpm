# ADR-012: Compose service prefix from `.env` (4.7)

**Status:** accepted (4.7.0-dev)  
**Date:** 2026-06-27

## Context

By default odpm generates a docker-compose stack with logical service keys `db` and `odoo`, postgres volume `postgres-data`, and Docker Compose project name derived from the project directory. On a shared host, multiple odpm projects can collide on service DNS names, volume names, and container project scope.

Since 4.6, `POSTGRES_SERVICE_NAME` in `.env` can rename **only** the postgres service (and sync `db_host` in `odoo.conf`). Odoo remains `odoo`; manifest sidecars keep literal `depends_on: ["db"]`; named volumes are unchanged.

Goal (4.7 track B): optional **`ODPM_COMPOSE_PREFIX`** in `.env` for **full-stack isolation** — service keys, named volumes, and compose project name — while manifest and plugins keep **logical** names (`db`, `odoo`).

## Decision

### New `.env` variable

| Variable | Required | Meaning |
|----------|----------|---------|
| `ODPM_COMPOSE_PREFIX` | No | Prefix for compose service keys, postgres volume, and project name |

When **unset or invalid**, behaviour matches **4.6** (legacy).

### Normalization

- Input lowercased; allowed charset: `[a-z0-9-]+` (must start with `a-z` or `0-9`… plan says lowercase letters digits dash — use `^[a-z][a-z0-9-]*$` after lowercasing, same family as `POSTGRES_SERVICE_NAME`).
- Trailing `-` is optional in `.env`; host normalizes to **canonical prefix with trailing `-`** for name composition (e.g. `acme` → `acme-`).

### Physical names (when prefix active)

| Logical | Physical example (`ODPM_COMPOSE_PREFIX=acme`) |
|---------|-----------------------------------------------|
| postgres service | `acme-db` |
| odoo service | `acme-odoo` |
| postgres named volume | `acme-postgres-data` |
| compose project `name:` / `-p` | `acme` (slug **without** trailing `-`) |

Manifest `services.*.depends_on: ["db"]` stays logical until `apply_compose_prefix` in compose generation ([ADR-009](adr-009-compose-service-patch.md)).

String fields that need the **hostname** of a stack service (notably `environment` / `command`) use **`${@service:<logical>}`** ([env substitution](../reference/odpm-json.md)): resolved via `ComposeNamingContext` / `map_logical_service_name` when the manifest is expanded (`db` → physical postgres, `odoo` → physical odoo, other keys identity). Wiring: `EnvResolver.compose_naming` from `compose_naming_from_user_env` on bootstrap; preserved across `inject_service_source_paths`.

### Legacy `POSTGRES_SERVICE_NAME`

| Mode | Behaviour |
|------|-----------|
| Prefix **empty** | `POSTGRES_SERVICE_NAME` sets postgres service (default `db`); odoo = `odoo` |
| Prefix **set** | Derived `{prefix}db`, `{prefix}odoo`, …; **`POSTGRES_SERVICE_NAME` ignored** with warning |

### Host API (4.7 B0)

- `dev_project/compose/service_names.py` — `parse_compose_prefix`, `ComposeNamingContext`, `resolve_compose_naming`.
- `ParsedUserEnv` / `CreateUserEnvironment` expose `compose_prefix`, `compose_project_name`, `odoo_service_name`, `postgres_volume_name`, and effective `postgres_service_name`.

### Compose document rewrite (4.7 B1)

- `apply_compose_prefix` / `apply_compose_physical_names` in `service_names.py` — rewrite service keys, `depends_on`, named volumes, top-level `name:`.
- `compose_document.py` builds with logical `db` / `odoo`, then applies physical names from `user_env`.

### Deferred (B3)

- User docs in `env-dotenv.md` (B3).

### Runtime wire (4.7 B2)

- `compose/runtime.py` — physical `odoo_service_name` / `postgres_service_name`; `compose_cli_argv` adds `-p` when prefix active.
- `database/compose_exec.py`, `runtime_coordinator.py` — all compose CLI invocations use `compose_cli_argv`.
- `database/state.py` / drift — snapshot includes `compose_project_name` and `odoo_service_name`; drift kind `compose_project_name`.

## Consequences

- **New:** `dev_project/compose/service_names.py`, constant `ODPM_COMPOSE_PREFIX_ENV`.
- **Tests:** `tests/test_compose_service_names.py`.
- **Related:** [ADR-011](adr-011-scenario-manifest-overrides.md) (scenario overlays use logical compose names); [ADR-014](adr-014-compose-stack-network.md) (optional stack network from `.env`, physical rewrite after prefix).

## References

- Plan: `.cursor/plans/4.7_scenarios_compose_prefix_9b4acf8a.plan.md`
- [ADR-009](adr-009-compose-service-patch.md) — logical service names in manifest
- [ADR-014](adr-014-compose-stack-network.md) — compose stack network (track D)
