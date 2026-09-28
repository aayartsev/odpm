# ADR-015: Manifest `service_sources` for sidecar git contexts

**Status:** accepted (4.7.0-dev)  
**Date:** 2026-07-14

## Context

Manifest v2 `services` and `hooks.post_prepare` often need a **host path** to an external repository (sidecar emulator, `docker build` context). Teams used project `.env` variables such as `DIGITAL_AUTOPARTS_ENV_DIR` and `${VAR}` in manifest strings. That works but is machine-specific and not committed as stack intent.

Git materialize already exists for `platform`, `developing`, and `dependencies`, but those repos feed **addons** / dependency resolution — not arbitrary compose build contexts.

## Decision

### Manifest

- New optional object **`service_sources`**: map `name → git link` (same link grammar as [git-links.md](../reference/git-links.md)).
- Optional **`services.<svc>.source`**: documents binding to a `service_sources` name; validated against the effective slice.
- Scenario overlays: **`service_sources` merge replace-by-name** (same as `services` replace-by-name, not list concat).

### Runtime

- Prepare step **`sources.materialize`** after `git.materialize`, before `hooks.post_clone`.
- Clone target: **`${ODOO_PROJECTS_DIR}/service-sources/<name>`** — never `dependencies_projects` / `addons_path`.
- Env placeholder **`${@source:<name>}`** → `ODPM_SOURCE_<NAME>`; compose fields with `@source` are re-expanded after materialize.
- `file://` links skip clone (local override).

### Lock

- Extend `.odpm/deps.lock.json` schema v1 with optional **`service_sources`** map keyed by **name** (not URL-only list).
- Collect / apply / verify in `DepsLockManager` alongside existing git locks.

### Out of scope

- Automatic `docker compose build` / `build.context` in compose schema
- Auto-mount entire source repo into Odoo volumes
- GC of old `service-sources/` directories
- Nested dependency `odpm.json` `service_sources`

## Consequences

- Sidecar stacks can declare git URLs in committed manifest; laptop and CI share the same intent.
- Legacy `${VAR}` paths in `.env` remain valid.
- Plan registry gains `sources.materialize`; compose fragment input strips manifest-only `source` field.
