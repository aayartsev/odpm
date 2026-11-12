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
5. **Layered CI images (ADR-027):** `odpm image base ensure` is the explicit base stage; `odpm build` runs base → platform → venv → optional deps → app (no monolithic final `dockerfile_ci` with in-app bake venv). Kaniko/docker backends unchanged.
6. Platform/app Dockerfiles `FROM` resolved base / parent layer refs via the same builder factory.
7. **Noninteractive apt in base templates:** `ENV DEBIAN_FRONTEND=noninteractive` plus `apt-get -y -o Dpkg::Options::="--force-confdef" -o Dpkg::Options::="--force-confold" install …` in all `debian_*_dockerfile*` profiles. Needed for kaniko `direct`, where the executor may see host `/etc` (e.g. existing `sudo.conf`) and otherwise blocks on a conffile prompt without a TTY.
8. **Host `statoverride` / `messagebus`:** kaniko `direct` can also expose host `/var/lib/dpkg/statoverride` (e.g. dbus → group `messagebus`). All base templates ensure that group exists before `apt-get install sudo`: `(getent group messagebus >/dev/null || groupadd -r messagebus)`.

## Consequences

- Full daemonless path: prepare + kaniko base push + kaniko final.
- Extends ADR-016 (base backend was previously out of scope).
- Manual kaniko smoke stays checklist-only; opt-in docker integration unchanged.

## References

- ADR-016, ADR-017, ADR-018
- [docs/scenarios/ci.md](../scenarios/ci.md)
