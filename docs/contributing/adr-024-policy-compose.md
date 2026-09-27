# ADR-024: Policy compose (scenario × security)

**Status:** accepted (4.7.0-dev)  
**Date:** 2026-09-27

## Context

Security profiles ([ADR-023](adr-023-security-profiles.md)) introduced a second axis on top of `ODPM_SCENARIO`. Defaults (`server` → `hardened`) and conflict rules (CI scenario-owned binds; no password bootstrap in `ci`) lived partly in `security_profiles.py` and partly inside `ScenarioPolicy.from_scenario`, which made combinations easy to desync.

Host gates (`SystemCheckPolicy`, [ADR-017](adr-017-ci-prepare-only-policy.md)) remain a third axis and are **not** composed here.

## Decision

- **`dev_project/policy_compose.py`** is the source of truth for:
  - `PRESETS` (scenario → default security profile)
  - `resolve_security_profile` / `security_profile_for_scenario`
  - `effective_binds` (including CI `(True, False)` topology)
  - `password_bootstrap_enabled` (hardened ∧ ¬ci)
- **`ScenarioPolicy.from_scenario`** remains the single public factory for `Config.policy`; it imports compose for profile/binds and keeps workflow-only branches (debugpy, venv, mounts, base image default).
- **`security_profiles.py`** keeps parsers, constants, secret refs, and `binds_for_security_profile(profile)`; scenario default helpers are lazy forwarders to compose (no module-level import cycle).
- **`Config.policy`** stays typed as `ScenarioPolicy` (no `PolicyBundle` on Config).

## Consequences

- New combinations are tested in `tests/test_policy_compose.py` (matrix A).
- HostGateInputs / explicit `SystemCheckPolicy` resolve is a follow-up, not this ADR.
- Docs: [security.md](../operations/security.md); amend ADR-023 References.

## References

- Implementation: `dev_project/policy_compose.py`, `dev_project/scenario_policy.py`, `dev_project/security_profiles.py`
- Related: [ADR-023](adr-023-security-profiles.md), [ADR-017](adr-017-ci-prepare-only-policy.md), [ADR-007](adr-007-base-image-profiles.md)
