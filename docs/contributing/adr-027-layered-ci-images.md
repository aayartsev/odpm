# ADR-027: Layered CI images (sources → ensure stages)

## Status

Accepted (4.8-dev track).

## Context

`odpm prepare` / `odpm build` historically produced one monolithic CI image (`dockerfile_ci`: `FROM` base, copy everything, bake venv in the final layer). Projects such as Akta duplicated staged registry layers in custom hooks. Stock odpm needs idempotent stages, selective rebuild by fingerprint, and clear separation of base / platform / optional dependencies / app / lint — without renaming scenario `ci` or base profile `ci` (ADR-007).

## Decision

1. **Flow:** `odpm prepare --stop-after sources` → analyse fingerprints / registry hit-miss (`odpm plan` + ensure logs) → `odpm image <layer> ensure` (or `odpm build` as shortcut).

2. **Stack:** `base → platform → venv → [deps] → app`; lint always `FROM` platform (no developing, no dependencies trees, no runtime venv required for hook bake). Optional **deps** when lock/manifest has at least one `dependencies` entry; otherwise deps ensure is noop and app `FROM` **venv**. **`odpm image venv ensure`** bakes `.venv` via `dev_project.bake_venv` using `ci/venv_install.json` with **container** paths (Odoo + `dev_project` already in the platform parent). **`odpm image lint ensure`** bakes the pre-commit hook cache inside the image via `dev_project.bake_pre_commit` (isolated `.odpm-lint-bake` git tree + config index + `pre-commit install-hooks` into the container user home cache); it does **not** run `pre-commit run --all-files` on application code (that stays in a later Job). Lint image build needs network so hooks can be cloned. Re-running bake skips commit when the index is unchanged.

3. **Families (docs/registry tags only):** `dev` ↔ profile `full`; `runtime` ↔ profile `medium`. Set via `ODPM_BASE_IMAGE_PROFILE`. Scenario `ODPM_SCENARIO=ci` and profile `ci` are **not** renamed; profile `ci` remains in ADR-007 but is not a target product family here (no wkhtml). Tag examples: `cache-platform-dev-…`, `cache-venv-dev-…`, `cache-platform-runtime-…`.

4. **Fingerprints (schema v1)** after sources: **platform** — Odoo pin, **platform** git SHA, profile, `dockerfile_platform` sha, python/distro/arch (no pip extras / venv_mode); **venv** — `platform_ref`, `venv_lock_hash`, extras from `requirements_txt`, `dockerfile_venv` sha; **deps** — dependency SHAs + parent-ref (venv); **lint** — pre-commit config hashes, `dockerfile_lint` sha, `bake_pre_commit.py` sha, platform fingerprint; **app** — `developing_git_sha` + parent-ref (deps or venv). `service_sources` never enter image fingerprints. Changing only pip extras / lock misses **venv** (and children), not platform.

5. **Presence:** base per ADR-019 (stamp); platform/venv/deps/app/lint remote refs via `crane digest` (fail-fast if missing); local via `docker image inspect`. `ODPM_IMAGE_FORCE_REBUILD=1` forces the current layer only. Publish-tag alias after kaniko (`--image-push`) uses `crane copy` when the fingerprint cache ref is not local.

6. **CLI:** `odpm image {base|platform|venv|deps|app|lint} ensure`; shared `--image-tag` / `--image-push` / `--image-builder` / `--from` / `--image-prune-stale` where applicable. Allowlisted under scenario `ci` (extends ADR-017). `odpm image … ensure` runs a scoped prepare: sources + secrets + **`template.dockerfile` / `template.dockerignore`** (so root build context tracks `.odpm` template upgrades on shared PVC; see ADR-007), not full compose / `template.odoo_conf` / docker-engine checks. **This coupling is intentional and stays:** the image layer build assumes a host-side sources snapshot (and secrets for optional app bake); there is no “build without prepare” mode in 4.8. Plan table labels separate preparation groups from `image.*` build steps. The **app** layer needs `odoo_config_data` (including `options`): `CiImageBuilder.prepare_app_build_context` refreshes secrets, reloads the manifest view, and calls `generate_odoo_conf_docker_data()` before writing `runtime/config.json` — without adding `template.odoo_conf` to `IMAGE_ENSURE_STEP_IDS`.

7. **Thin build contexts (miss path):** each layer writes only what it needs under `.odpm/{platform,venv,deps,app,lint}-build-context` — no “copy everything then strip”. Platform: `odoo/` + `dev_project/` (no `ci/`, no bake). Venv: `ci/venv_install.json` only. Deps: dependency trees from `mapped.local` excluding developing. App: developing + `odoo.conf` + `runtime/` (+ secrets when baked). Full `prepare_ci_build_context` remains for smoke tests only; layered `ensure_*` does not call it.

8. **Stale cache prune (opt-in):** `ODPM_IMAGE_PRUNE_STALE=1` or `--image-prune-stale` on `image … ensure` / `build`. After a **successful** ensure of platform/venv/deps/app/lint (hit or miss; nested parent ensures included), delete other tags matching `cache-{layer}-{family}-{odoo_version}-{build_date}-v-*` in the same repository, keeping the current fingerprint ref. Floating tags (`mr-*`, publish `--image-tag`) are never pruned. Tags with a **different** `build_date` in the name are out of scope. Remote: `crane ls`/`delete` plus best-effort local `docker rmi`; local-only: `docker` only. **Presence** without crane remains fail-fast; **prune** without crane / on delete errors is fail-soft (log only). `base` and deps noop (`return None`) do not prune.

9. **Deps context:** exclude developing by absolute mapped path (never basename-only), so dependency trees that share a folder name with the app are kept.

10. **`odpm build`:** only layered path (base → platform → venv → deps? → app). Monolithic final `dockerfile_ci` bake-in-app path removed. Old `cache-platform-*` tags that baked venv inside platform are **not** compatible as parents of deps/app after this change — one warm-up of the new chain is required.

11. **Templates:** `dev_project/templates/dockerfile_{platform,venv,deps,app,lint}` + matching `dockerignore_*` (no separate `dockerignore_venv` when the context is only the install JSON). Deps/app Dockerfiles keep ARG name `PLATFORM_IMAGE` (value is the venv or deps parent ref).

12. **Sources change check by input blocks (scenario `ci` only):** on `prepare --stop-after sources` and prepare inside `image … ensure`, odpm compares each layer’s fingerprint + registry/local presence **before** creating the Odoo worktree/classic tree for that layer. Modules: `dev_project/prepare/sources_change_check.py`, `dev_project/image_layers/source_plan.py`.

    | Block | When tree/materialize is skipped |
    |-------|----------------------------------|
    | platform | image hit → no `git.materialize_platform` / no Odoo checkout |
    | venv | hash `requirements.txt` from disk **or** `git show <pin>:requirements.txt` on a **bare** store (always bare for hash, classic or worktree); miss rebuilds `FROM` platform image — no Odoo tree required |
    | deps | hit or no deps → no `git.materialize_dependencies` |
    | app | developing SHA (`rev-parse`, or `ODPM_DEVELOPING_GIT_SHA` / `CI_COMMIT_SHA` for early plan) |
    | lint | pre-commit files in developing; miss does **not** require platform tree |

    Order: lock → materialize developing → ensure platform bare+pin → analyse blocks → conditional platform tree → conditional deps → sources tail. Tail without Odoo tree: `git.checkout` skips platform; `project.map_folders` does not require a live Odoo path; `project.update_links` skips module links into `odoo_src/.../addons`. Fail-soft: if presence/analysis fails (e.g. no `crane` for remote) → WARN + full materialize. Escape hatch: `ODPM_FORCE_FULL_SOURCES=1`. Outside scenario `ci` → full materialize as before.

## Consequences

- Breaking for consumers of monolithic `Dockerfile.ci` layout and for pipelines that treated platform as the baked-venv parent; documented in CHANGELOG.
- Job / operator wrappers (e.g. Akta) must call `odpm image venv ensure` (or `odpm build`) before deps/app; otherwise the app image lacks `.venv`.
- Extends ADR-016/019 backends; amends ADR-017 allowlist and ADR-019 “no separate base command / single final”.

## References

- [ADR-007](adr-007-base-image-profiles.md), [ADR-016](adr-016-ci-image-build-backends.md), [ADR-017](adr-017-ci-prepare-only-policy.md), [ADR-019](adr-019-kaniko-base-image-build.md), [ADR-026](adr-026-cli-command-verbs.md)
- [prepare-zones.md](prepare-zones.md) — visible prepare step zones and ensure ↔ sources coupling
- [docs/scenarios/ci.md](../scenarios/ci.md), [docs/reference/cli.md](../reference/cli.md)
