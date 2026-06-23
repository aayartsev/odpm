# ADR-007: Scenario base Dockerfile profiles (4.5)

**Status:** accepted (4.5-dev)  
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

## Related

- Phase S in roadmap 4.5
- [ci scenario](../scenarios/ci.md), [server scenario](../scenarios/server.md)
- `dev_project/dockerfile_profiles.py`
