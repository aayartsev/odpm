# ADR-025: Local sidecar gates (user_settings.sidecars)

**Status:** accepted (4.7.0-dev)  
**Date:** 2026-09-27

## Context

Developer stacks often declare many compose sidecars in shared `odpm.json` / scenario overlays. JSON cannot be commented, so temporarily turning services off for a faster local loop meant editing the shared manifest or hand-editing generated compose. That conflicts with the config split: team stack vs personal workflow.

## Decision

- **Source of truth:** optional `sidecars` map in `user_settings.json` — logical compose sidecar name → JSON boolean.
  - `false` — exclude from the effective set.
  - missing key or `true` — keep.
  - Default when absent/`null`: all enabled (`{}`).
- **Strict booleans only** — strings / `0` / `1` raise `ConfigError` (no `bool(x)` coercion).
- **Built-in `db` / `odoo` cannot appear** in the map (`ConfigError`). Gates apply only to sidecars (manifest `services` + plugin fragments).
- **Generate-time drop** (not Compose `profiles`): plan fragment steps, `.odpm/compose/fragments/*.yml`, and `docker-compose.yml` share one effective sidecar set.
- **Document pipeline order:** collect all sidecars → merge with `db`/`odoo` → apply `service_patches` → `apply_sidecar_gates` → `scrub_service_deps` → physical names. Patches targeting a locally disabled sidecar succeed, then the service is dropped (avoids *unknown service* on patch).
- **Plan / fragment evaluate+exec:** `collect_effective_compose_services` = collect → gate (no base/patches).
- **Dependency scrub** only for **list** `depends_on` / `links` (same as prefix rewrite). Long-form dict `depends_on` is out of scope.
- Changing `sidecars` changes the fragment snapshot input → rematerialize / regenerate compose (same as other settings that affect generated files: run `odpm --skip-start`).
- **`service_sources` materialize for disabled sidecars** remains unchanged in v1 (follow-up).

## Consequences

- Personal `sidecars: {…: false}` in a committed `user_settings.json` can surprise teammates/CI — document as local override; coordinate before committing disables.
- Unknown names in the map log a warning (including `true`); they do not fail the run.
- Implementation: `dev_project/compose/sidecar_gates.py`; wired from `build_compose_document`, `fragments_preview`, `evaluate_compose_fragments`, `exec_compose_fragments`.

## References

- Docs: [user-settings.md](../reference/user-settings.md), [config-split.md](../reference/config-split.md), [plugins.md](../reference/plugins.md)
- Related: [ADR-009](adr-009-compose-service-patch.md), [ADR-011](adr-011-scenario-manifest-overrides.md)
