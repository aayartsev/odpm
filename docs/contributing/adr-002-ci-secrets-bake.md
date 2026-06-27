# ADR-002: CI module secrets bake (TD-FEAT-09 Phase B)

## Status

Accepted (4.4 debt closure Phase 1).

## Context

odpm 4.3+ provides **developer/server** module secrets via `.odpm/secrets.json` → `.odpm/runtime/secrets.json` → read-only mount `/run/odpm/secrets.json` (`ODPM_SECRETS_PATH`). In scenario **`ci`**, host mount is disabled (`ScenarioPolicy.mount_runtime_secrets_from_host()` is false); prepare step `secrets.materialize` is **skip**.

CI pipelines still need module API keys inside the **baked image** without mounting secrets from the build runner filesystem at runtime.

## Decision

Two explicit delivery paths:

| Scenario | Secrets delivery | Mechanism |
|----------|------------------|-----------|
| `developer`, `server` | Host mount at runtime | `--secrets-file` or manual `.odpm/secrets.json`; `secrets.materialize` on prepare |
| `ci` | Baked into image | `ODPM_BAKE_SECRETS=1` + secrets source on build runner during `odpm --build-image` |

### CI bake flow

1. On the build runner, provide secrets **before** image build:
   - `odpm --secrets-file /secure/ephemeral.json` (writes `.odpm/secrets.json`), or
   - copy `.odpm/secrets.json` from a secure store.
2. Build with explicit opt-in:
   ```bash
   export ODPM_BAKE_SECRETS=1
   odpm --build-image --image-tag registry/project:tag
   ```
3. `CiImageBuilder.prepare_ci_build_context()` materializes runtime JSON (even though prepare skips it in ci) and copies `runtime/secrets.json` into the Docker build context.
4. Generated `Dockerfile.ci` adds:
   - `COPY runtime/secrets.json /run/odpm/secrets.json`
   - `ENV ODPM_SECRETS_PATH=/run/odpm/secrets.json`
5. Runtime `docker compose` for ci **does not** mount secrets from the host; modules read the baked file.

### Safety rules

- Bake is **opt-in** (`ODPM_BAKE_SECRETS=1|true|yes`). Without the flag, no secrets COPY in Dockerfile.
- Without `.odpm/secrets.json` (or after failed materialize), bake is a no-op.
- Secrets values must not appear in build logs or plan diff (unchanged policy).
- **Not in scope:** SOPS/Vault encryption, server-side secret rotation (future).

## Consequences

- CI operators document ephemeral secret injection on the runner, then bake — not host mount.
- `tests/test_ci_secrets_smoke.py` covers developer mount and ci bake context/dockerfile generation.
- `tests/odpm_subprocess.py` stabilizes CLI subprocess tests without relying on `odpm.py` + implicit `pluggy` path.

## References

- [docs/operations/secrets.md](../operations/secrets.md)
- [docs/scenarios/ci.md](../scenarios/ci.md)
- TD-FEAT-09 (closed; см. CHANGELOG)
