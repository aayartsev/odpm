# ADR-007: Scenario base Dockerfile profiles (4.5)

**Status:** accepted (4.5-dev); amended 4.7.0-beta  
**Date:** 2026-06-22

## Context

All scenarios previously shared one base Dockerfile template per distro (`debian_12_dockerfile`), embedding Chromium, Xvfb, and VS Code server paths into CI base images. `ensure_base_image()` only compared Unix user/uid/gid in `base_image_identity.json`; template or scenario changes did not trigger rebuild.

## Decision

### Three profiles

| Scenario | Profile | Base image contents |
|----------|---------|---------------------|
| `developer` | **full** | Browser stack, Xvfb, `.vscode-server`, wkhtmltopdf, pre-commit, uv |
| `server` | **medium** | Odoo build deps + wkhtmltopdf; no browser/Xvfb/IDE paths |
| `ci` | **ci** | Minimal runtime + `bake_venv` deps; no browser/Xvfb/wkhtmltopdf/IDE |

`ScenarioPolicy.base_image_profile` selects the program template  
`{distro}_{ver}_dockerfile_{profile}` with fallback to legacy `{distro}_{ver}_dockerfile` when profile variants are absent (Ubuntu/Debian 11 until extended).

### Explicit profile override (4.7.0-beta)

When the scenario default profile is wrong for a project (e.g. `ci` needs wkhtmltopdf from **medium**, or `developer` wants a slim **ci** base), set **`ODPM_BASE_IMAGE_PROFILE`** to `full`, `medium`, or `ci`.

- Process env wins over layered `.env` (same as other odpm keys).
- Invalid / blank values fall back to the scenario default (warning logged).
- Override changes only the **base Dockerfile / image tag / identity fingerprint**; other scenario policy (debugpy, postgres bind, mounts, etc.) stays tied to `ODPM_SCENARIO`.
- Prefer this over inventing raw template names.

`ScenarioPolicy.from_scenario(..., base_image_profile=)` applies `resolve_base_image_profile()`.

### Image tags

`odoo_image_name` includes profile suffix:  
`odoo-{arch}-python-{py}-{distro}-{ver}-{profile}`.

### Identity fingerprint

`base_image_identity.json` records `user`, `uid`, `gid`, `base_image_profile`, and `dockerfile_sha256` (hash of project-root `Dockerfile`). `ensure_base_image()` rebuilds when any field drifts.

### Template sync

`ProjectDirManager.ensure_project_template()` upgrades `.odpm/*_dockerfile_*` when program template **sha256** differs from the project copy (in addition to marker checks).

## Consequences

- Debian 12/13 ship `*_full`, `*_medium`, `*_ci` templates in 4.5; other distros use legacy single template until follow-up.
- First run after upgrade may rebuild base image once (expected).
- `odpm plan` step `template.dockerfile` reports identity mismatch when profile or Dockerfile hash changes.
- Changing `ODPM_BASE_IMAGE_PROFILE` rebuilds the base image (tag and identity include the profile).

## Related

- Phase S in roadmap 4.5
- [developer](../scenarios/developer.md), [server](../scenarios/server.md), [ci](../scenarios/ci.md) scenarios
- [`.env` reference](../reference/env-dotenv.md), [generated files](../reference/generated-files.md)
- `dev_project/dockerfile_profiles.py`
