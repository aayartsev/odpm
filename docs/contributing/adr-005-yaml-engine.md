# ADR-005: Host YAML engine (4.5)

**Status:** accepted (4.5-dev)  
**Date:** 2026-06-22

## Context

odpm 4.4 generated `docker-compose.yml` via a string template and a hand-rolled YAML scalar renderer (`compose/command_render.py`, `compose/fragments.py`). That approach was stdlib-friendly but hard to extend for structured merge, deterministic service ordering, and plugin fragment composition.

Phase Y (YAML engine) centralizes host-side YAML in `dev_project/yaml/` while keeping container `ContainerConfig` stdlib-only.

## Decision

### Library

- Host dependency: **`ruamel.yaml>=0.18`** (round-trip, ordered mappings).
- PyYAML remains allowed in **docs tooling only** (`scripts/patch_mkdocs_bootstrap.py`); not a host runtime dependency for compose.

### Module boundary

| Module | Role |
|--------|------|
| `dev_project/yaml/engine.py` | `load_document`, `dump_document`, `merge_services`, `merge_services_with_patches` (4.6) |
| `dev_project/compose/compose_document.py` | Build structured compose dict |
| `dev_project/compose/generator.py` | Single `dump_document` at end |
| `dev_project/compose/validate.py` | Structural compose validation (4.6 D5) |
| `dev_project/compose/command_render.py` | Thin wrappers over engine (legacy API) |

Container code **must not** import `dev_project.yaml`.

### Compose generation

- `ComposeGenerator` builds a **dict** (`services`, `volumes`) instead of formatting a line-oriented template.
- Extra manifest/plugin services merge via `merge_services`; **same service name → overlay replaces the whole service** (plugin wins over manifest).
- Built-in `odoo` / postgres patches use manifest `service_patches` and `merge_services_with_patches` (4.6+, [ADR-009](adr-009-compose-service-patch.md)).
- Exec-form `command:` lists serialize as YAML sequences with quoted numeric/boolean-like strings (Docker Compose YAML 1.1 compatibility).

### Amendment (4.6.0)

- `dev_project/yaml/engine.py` also exports `merge_services_with_patches` (see ADR-009).
- ADR-005 “deep merge per key” for `merge_services` was **never implemented** in 4.5; 4.6 documents replace-by-name and defers partial built-in patches to `service_patches`.

### Amendment (4.6.0 D5)

- **`dev_project/compose/validate.py`** — structural validation of generated compose documents (services mapping, non-empty `image`, list-shaped fields, `environment` shape).
- **`ComposeGenerator`** validates the document before YAML dump; prepare step **`compose.validate`** runs `check_docker_compose()` plus on-disk `validate_compose_file()`.
- **Golden snapshots** — `tests/fixtures/compose/golden/{developer,server,ci}.yml` compared by `tests/test_compose_golden_scenarios.py`.
- **`docker-compose.override.yml` merge** — still deferred.

### Explicit non-goals (4.5.0)

- **YAML anchors/aliases** — not supported; document limitation in plugin docs.
- **`docker-compose.override.yml` merge** — deferred (optional Y3).
- **JSON Schema validation of generated compose** — replaced by structural validation in D5 (no external schema file).

User-visible `docker-compose.yml` output remains stable for existing contract tests; internal APIs may change.

## Consequences

- `pyproject.toml` and Debian `Depends` include `ruamel.yaml`.
- Contract suite: `tests/test_yaml_engine.py`, existing `test_compose_*` / `test_start_command` remain green.
- `docs/reference/plugins.md` updated: host yaml engine instead of “no PyYAML”.
