# ADR-023: Security profiles (convenience / hardened)

**Status:** accepted (4.7.0-dev)  
**Date:** 2026-09-26

## Context

`ODPM_SCENARIO` mixes topology/workflow (debugpy, volumes, CI bake) with security posture (weak passwords, published-port binds). Teams need laptop-friendly defaults and server hardening, plus the ability to override posture without switching scenario (e.g. `developer` + hardened binds for a prod-like dry run).

## Decision

Add a **security profile** axis on `ScenarioPolicy`:

| Profile | Scenario default | Passwords (new files) | Publish binds |
|---------|------------------|----------------------|---------------|
| `convenience` | `developer` | plaintext `1` / `admin` | not forced to localhost |
| `hardened` | `server` | `${@secret:…}` + bootstrap random keys in `.odpm/secrets.json` | postgres + all published → `127.0.0.1` |

- Override: `--security-profile` > `ODPM_SECURITY_PROFILE` > scenario default (same precedence pattern as `--secrets-provider`).
- **`ci`**: never bootstrap Odoo password secrets; port binds stay scenario-owned regardless of override.
- **SoT for Odoo passwords:** expanded `user_settings.json`. Existing settings files are never rewritten; hardened emits WARNING on raw plaintext password fields.
- Bootstrap is two-phase so Infisical/manifest fetch can run after `developing_project`: phase1 expand pre-manifest fields → secrets fetch → ensure password keys → availability gate → phase2 deep-expand settings.
- Availability gate for `${@secret:}` (manifest + settings) runs **after** password-key ensure.
- Not moved into the profile: debugpy, `dev_mode`, restart policy, venv, base image (scenario / ADR-007).

## Consequences

- Compose golden/bind tests must assert profile (and overrides), not only scenario name.
- Follow-ups (PG password → secrets, separate PG admin/app passwords) reuse the same axis; see `.cursor/todo-security-profiles.md`.

## References

- Implementation: `dev_project/security_profiles.py`, `ScenarioPolicy.security_profile`
- Docs: `docs/operations/security.md`
