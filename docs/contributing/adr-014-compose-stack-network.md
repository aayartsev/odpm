# ADR-014: Compose stack network from `.env` (4.7)

**Status:** accepted (4.7.0-dev)  
**Date:** 2026-06-23

## Context

By default odpm generates `docker-compose.yml` with `services` and `volumes` only. There is no top-level `networks:` section; built-in `db` / `odoo` and manifest sidecars attach to Docker Compose **implicit default network** for the project.

On a shared host this is enough for a single odpm stack. Two common extensions require an **explicit** network:

| Scenario | Need |
|----------|------|
| Reverse proxy (Traefik, Caddy) | Attach odoo stack to an existing **external** network (`proxy`) |
| Named isolation | Declare a **managed** bridge network instead of implicit default |

Manifest v2 sidecars may already include `networks` in their compose spec (`${VAR}` expansion at load — [ADR-009](adr-009-compose-service-patch.md)). odpm does not declare matching top-level `networks:` or attach built-in services, so custom sidecar networks are incomplete without manual YAML edits.

Goal (4.7 track D): optional **one** compose network for the **whole** odpm stack from `.env`, consistent with [ADR-012](adr-012-compose-service-prefix.md) (physical naming) and [ADR-013](adr-013-layered-env-dotenv.md) (home + project `.env` merge).

## Decision

### New `.env` variables

| Variable | Required | Meaning |
|----------|----------|---------|
| `ODPM_COMPOSE_NETWORK` | No | Logical network name; when unset, behaviour matches pre–track D (implicit default, no `networks:` in YAML) |
| `ODPM_COMPOSE_NETWORK_EXTERNAL` | No | When truthy (`1`, `true`, `yes`), network is **external** (must exist on the host); default **managed** bridge |

`ODPM_COMPOSE_NETWORK_EXTERNAL` **without** `ODPM_COMPOSE_NETWORK` has no effect — an explicit network name is required.

### Default / backward compatibility

When `ODPM_COMPOSE_NETWORK` is **unset or invalid**:

- Generated compose has **no** `networks:` section.
- Services have **no** `networks:` field.
- Docker Compose creates the usual implicit project default network — same as 4.6 / 4.7 tracks A–C.

Invalid network names (see normalization) log a **warning** and fall back to this default.

### Normalization

- Input lowercased; allowed charset: `^[a-z][a-z0-9-]*$` (same family as `ODPM_COMPOSE_PREFIX`).
- The `.env` value is the **logical** network key used in the compose document before physical rewrite.

Constant `LOGICAL_STACK_NETWORK = "stack"` in code is the conventional default name in docs and examples; the logical key is whatever the user sets (`stack`, `proxy`, …). Manifest sidecars referencing `networks: ["stack"]` are consistent only when `ODPM_COMPOSE_NETWORK=stack`.

### Physical names

| Mode | Physical network name |
|------|------------------------|
| Managed, no prefix | Same as logical (e.g. `stack`) |
| Managed, `ODPM_COMPOSE_PREFIX=acme` | `{prefix}{logical}` (e.g. `acme-stack`) |
| External | Logical name **as-is** — **no** prefix (shared host networks like `proxy`) |

External networks are declared as:

```yaml
networks:
  proxy:
    external: true
```

Managed networks:

```yaml
networks:
  stack:
    driver: bridge
```

(Exact driver options deferred; bridge default is sufficient for 4.7.)

### Service attachment

When a network is active:

1. Add top-level `networks:` with the resolved definition.
2. For **each** service in the merged stack (`db`, `odoo`, sidecars) that does **not** already define `networks`, set `networks: [<logical_name>]`.
3. Services that **already** have `networks` are **not** overwritten; only logical→physical name rewrite applies (same pattern as `depends_on` in [ADR-012](adr-012-compose-service-prefix.md)).

All attached services share one L2 domain; inter-service DNS uses **compose service keys** (`db`, `acme-odoo`, …). `db_host` in `odoo.conf` is unchanged.

### Integration with prefix layer

Network rewrite runs in `apply_compose_physical_names` **after** `apply_compose_prefix` and legacy postgres rename:

```text
logical compose document
  → apply_compose_prefix (services, volumes, depends_on)
  → legacy POSTGRES_SERVICE_NAME rename
  → apply_compose_network (networks keys, service.networks[])
```

Module: `dev_project/compose/network_names.py` — `ComposeNetworkContext`, `resolve_compose_network`, `apply_compose_network`.

Host parse: `dev_project/host/user_env_parse.py` — `parse_compose_network_name`, `parse_compose_network_external`; fields on `ParsedUserEnv` / `CreateUserEnvironment`.

### Layered `.env` ([ADR-013](adr-013-layered-env-dotenv.md))

Typical split:

- `~/.odpm/.env` — `ODPM_COMPOSE_NETWORK=proxy`, `ODPM_COMPOSE_NETWORK_EXTERNAL=1`
- `<project>/.env` — `ODPM_COMPOSE_PREFIX=acme`, `ODPM_COMPOSE_NETWORK=stack` (project wins on collision)

### Database drift / snapshot

Network name is **not** stored in `last_run.json` and does **not** introduce a database drift kind. Regenerating `docker-compose.yml` on env change follows existing compose materialize behaviour.

### Cross-stack DNS (operational note)

Containers on the same user-defined network can reach each other when Docker registers matching network aliases. Stacks from **different** compose projects on one external network should use **unique** service names (e.g. via `ODPM_COMPOSE_PREFIX`) to avoid collisions on short names like `odoo`. Detailed proxy examples live in user docs (`plugins.md`, `env-dotenv.md`).

### Out of scope (4.7)

- Top-level `networks` in `odpm.json` or `scenarios.*`
- Multiple simultaneous stack networks (e.g. `stack` + `proxy` on different services)
- `odpm network create` helper
- Per-scenario network overlays
- Database drift kind for network changes

## Consequences

- **New:** `dev_project/compose/network_names.py`, constants `ODPM_COMPOSE_NETWORK_ENV`, `ODPM_COMPOSE_NETWORK_EXTERNAL_ENV`.
- **Changed:** `compose_document.py`, `service_names.apply_compose_physical_names`, `compose/validate.py` (structural checks for `networks`).
- **Tests:** `tests/test_compose_network.py` (planned).
- **Related:** [ADR-012](adr-012-compose-service-prefix.md), [ADR-013](adr-013-layered-env-dotenv.md), [ADR-009](adr-009-compose-service-patch.md).

## References

- Plan: `.cursor/plans/4.7_compose_networks_7e7ac174.plan.md`
- [env-dotenv.md](../reference/env-dotenv.md) — user-facing variable docs (track D5)
- [plugins.md](../reference/plugins.md) — reverse-proxy examples (track D5)
