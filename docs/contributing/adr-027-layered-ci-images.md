# ADR-027: Layered CI images (sources → ensure stages)

## Status

Accepted (4.8-dev track).

## Context

`odpm prepare` / `odpm build` historically produced one monolithic CI image (`dockerfile_ci`: `FROM` base, copy everything, bake venv in the final layer). Projects such as Akta duplicated staged registry layers in custom hooks. Stock odpm needs idempotent stages, selective rebuild by fingerprint, and clear separation of base / platform / optional dependencies / app / lint — without renaming scenario `ci` or base profile `ci` (ADR-007).

## Decision

1. **Flow:** `odpm prepare --stop-after sources` → analyse fingerprints / registry hit-miss (`odpm plan` + ensure logs) → `odpm image <layer> ensure` (or `odpm build` as shortcut).

2. **Stack:** `base → platform → [deps] → app`; lint always `FROM` platform (no developing, no dependencies trees in the lint image). Optional **deps** when lock/manifest has at least one `dependencies` entry; otherwise deps ensure is noop and app `FROM` platform.

3. **Families (docs/registry tags only):** `dev` ↔ profile `full`; `runtime` ↔ profile `medium`. Set via `ODPM_BASE_IMAGE_PROFILE`. Scenario `ODPM_SCENARIO=ci` and profile `ci` are **not** renamed; profile `ci` remains in ADR-007 but is not a target product family here (no wkhtml). Tag examples: `cache-platform-dev-…`, `cache-platform-runtime-…`.

4. **Fingerprints (schema v1)** after sources: platform includes Odoo pin, extras, **platform** git SHA only, profile, dockerfile sha, python/distro/arch/venv; deps includes dependency SHAs + platform-ref; lint includes pre-commit config hashes; app includes `developing_git_sha` + parent-ref. `service_sources` never enter image fingerprints.

5. **Presence:** base per ADR-019 (stamp); platform/deps/app/lint remote refs via `crane digest` (fail-fast if missing); local via `docker image inspect`. `ODPM_IMAGE_FORCE_REBUILD=1` forces the current layer only. Publish-tag alias after kaniko (`--image-push`) uses `crane copy` when the fingerprint cache ref is not local.

6. **CLI:** `odpm image {base|platform|deps|app|lint} ensure`; shared `--image-tag` / `--image-push` / `--image-builder` / `--from` where applicable. Allowlisted under scenario `ci` (extends ADR-017). `odpm image … ensure` runs a scoped prepare (sources + secrets only), not full compose/template materialization.

7. **Deps context:** exclude developing by absolute mapped path (never basename-only), so dependency trees that share a folder name with the app are kept.

8. **`odpm build`:** only layered path (base → platform → deps? → app). Monolithic final `dockerfile_ci` bake-in-app path removed.

9. **Templates:** `dev_project/templates/dockerfile_{platform,deps,app,lint}` + matching `dockerignore_*`.

## Consequences

- Breaking for consumers of monolithic `Dockerfile.ci` layout; documented in CHANGELOG.
- Akta can thin `layered_hooks.py` after adoption (out of scope for this ADR).
- Extends ADR-016/019 backends; amends ADR-017 allowlist and ADR-019 “no separate base command / single final”.

## References

- [ADR-007](adr-007-base-image-profiles.md), [ADR-016](adr-016-ci-image-build-backends.md), [ADR-017](adr-017-ci-prepare-only-policy.md), [ADR-019](adr-019-kaniko-base-image-build.md), [ADR-026](adr-026-cli-command-verbs.md)
- [docs/scenarios/ci.md](../scenarios/ci.md), [docs/reference/cli.md](../reference/cli.md)
