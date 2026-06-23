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
| `dev_project/yaml/engine.py` | `load_document`, `dump_document`, `merge_services` |
| `dev_project/compose/compose_document.py` | Build structured compose dict |
| `dev_project/compose/generator.py` | Single `dump_document` at end |
| `dev_project/compose/command_render.py` | Thin wrappers over engine (legacy API) |

Container code **must not** import `dev_project.yaml`.

### Compose generation

- `ComposeGenerator` builds a **dict** (`services`, `volumes`) instead of formatting a line-oriented template.
- Manifest and plugin services merge via `merge_services`; same service name → overlay wins (deep merge per key).
- Exec-form `command:` lists serialize as YAML sequences with quoted numeric/boolean-like strings (Docker Compose YAML 1.1 compatibility).

### Explicit non-goals (4.5.0)

- **YAML anchors/aliases** — not supported; document limitation in plugin docs.
- **`docker-compose.override.yml` merge** — deferred (optional Y3).
- **JSON Schema validation of generated compose** — deferred (optional Y3).

User-visible `docker-compose.yml` output remains stable for existing contract tests; internal APIs may change.

## Consequences

- `pyproject.toml` and Debian `Depends` include `ruamel.yaml`.
- Contract suite: `tests/test_yaml_engine.py`, existing `test_compose_*` / `test_start_command` remain green.
- `docs/reference/plugins.md` updated: host yaml engine instead of “no PyYAML”.
