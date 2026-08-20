# ADR-019: Kaniko base + final image build

## Status

Accepted (4.7).

## Context

ADR-016 added Kaniko for the **final** CI image but left base image on `docker build` / `docker image inspect`. Daemonless CI still needed a pullable base. Builder selection now comes from layered `.env` (ADR-017).

## Decision

1. **`ImageBuildBackend` for base** — [`BaseImageBuilder`](../../dev_project/project_env/base_image.py) builds via the same factory as final (`docker` / `kaniko`).
2. **Registry prefix** — `ODPM_BASE_IMAGE_REGISTRY`; `ConfigPaths.resolve_base_image_ref(registry=…)` → `{registry}/{local}:{latest}`.
3. **Push policy (locked):**
   - `docker`: local tag, no base push;
   - `kaniko`: base **always** `push=True`; missing registry → fail-fast before build;
   - final push remains `--image-push` / `ODPM_CI_IMAGE_PUSH` only.
4. **Exists check:** kaniko uses identity stamp (+ optional `image_ref`); docker keeps `docker image inspect`.
   - **Stamp ≠ registry presence:** a matching local stamp skips rebuild even if the image was deleted from the registry. Stamp is gitignored (machine-local). If final `FROM` fails on pull, delete `.odpm/base_image_identity.json` (or force a Dockerfile/identity change) and rebuild.
5. **`--build-image`** always `ensure_base` then final; no `--build-base-image` in this release.
6. Dockerfile.ci `FROM` uses `resolve_base_image_ref()`.

## Consequences

- Full daemonless path: prepare + kaniko base push + kaniko final.
- Extends ADR-016 (base backend was previously out of scope).
- Manual kaniko smoke stays checklist-only; opt-in docker integration unchanged.

## References

- ADR-016, ADR-017, ADR-018
- [docs/scenarios/ci.md](../scenarios/ci.md)
