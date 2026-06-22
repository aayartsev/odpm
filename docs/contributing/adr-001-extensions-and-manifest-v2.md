# ADR-001: Extensions, manifest v2, and version axes

**Status:** accepted (4.4-dev)  
**Date:** 2026-06-16

## Context

odpm 4.4 is the last planned feature release. It introduces a plugin/extension API, compose fragments, manifest v2, and selective runtime dependencies on the host (`jsonschema`, `pluggy`). Container `ContainerConfig` validation stays stdlib-only.

Historically, flat `odpm.json` used a single field `odpm_version` both as a manifest contract marker and (incorrectly) compared against the manager version via `float()` in bootstrap. Manager releases and manifest format must be decoupled before `ODPM_VERSION` moves to `4.4`.

## Decision

### Version axes

| Axis | Constant / field | Example | Meaning |
|------|------------------|---------|---------|
| Product / CLI | `RELEASE_VERSION`, `ODPM_VERSION`, `odpm --version`, pip wheel, deb/rpm | `4.4.3` | Installed odpm version (single user-facing value) |
| Manifest schema | `manifest_schema` in JSON | `1`, `2` | Shape and semantics of `odpm.json` |
| Min manager (v2 only) | `requires_odpm` | `4.4.3` | Semver: installed manager must be ≥ this |
| Legacy flat contract | `odpm_version` (v1 only) | `4.0` | Manifest contract line, **not** manager version |

`ODPM_VERSION` is an alias of `RELEASE_VERSION`. Pip, deb, and `odpm --version` always show the same patch release.

`odpm_version` in flat manifests is **deprecated** in favour of `manifest_schema` + `requires_odpm`. It remains readable for v1 projects.

### Manifest v1 (flat, default)

Implicit `manifest_schema: 1` when `manifest_schema` is absent. Supported `odpm_version` contract lines: `3.0`, `4.0`. Manager `4.4` reads v1 manifests without requiring projects to bump `odpm_version` to `4.4`.

New flat manifests written by odpm 4.4 still use `odpm_version: "4.0"` (`MANIFEST_V1_CONTRACT_LINE`) until the project migrates to v2.

### Manifest v2 (nested)

Top-level `manifest_schema: 2` and `requires_odpm` (required). Nested shape (conceptual):

```json
{
  "manifest_schema": 2,
  "requires_odpm": "4.4.3",
  "platform": { "git": "...", "build_date": "latest" },
  "python": "3.12",
  "distro": { "name": "debian", "version": "13" },
  "postgres": "15",
  "dependencies": [],
  "requirements": [],
  "developing": { "git": "..." },
  "locks": {
    "git": { "https://github.com/OCA/web.git 19.0": "abc123..." },
    "venv": "sha256:..."
  },
  "hooks": { "post_prepare": [], "pre_up": [] },
  "services": {}
}
```

Validation: **jsonschema** + packaged JSON Schema files under `dev_project/manifest/schemas/` (implemented in epic manifest-v2-core).

### Locks

`locks` in manifest v2 is the **declarative** contract (git URL → commit, venv hash). `.odpm/deps.lock.json` remains the operational artifact for prepare/CI; `DepsLockManager` will sync from manifest `locks.git` when `manifest_schema: 2` (epic manifest-migrate-locks). v1 projects without `locks` keep using `deps.lock.json` only.

### Host runtime dependencies

| Package | Role |
|---------|------|
| `packaging` | Semver parsing (existing) |
| `jsonschema` | Manifest v2 JSON Schema validation |
| `pluggy` | Entry points `odpm.prepare_steps`, later `odpm.hooks` |

Subprocess git/docker on the host remain default; no mandatory `docker`/`git` PyPI libs.

### Plugin public API (target)

- Frozen dataclasses (`ExtensionHostContext`, hook contexts) — no direct `Config.__dict__` access.
- Registry pattern: [dev_project/debugger/backends.py](../../dev_project/debugger/backends.py).
- Prepare steps: extend [dev_project/prepare/registry.py](../../dev_project/prepare/registry.py) via pluggy; `evaluate` must stay side-effect free for `odpm plan`.
- Compose: YAML **fragments** merged into generated `docker-compose.yml` (epic compose-fragments).

### Hooks lifecycle order

1. Prepare steps (built-in + plugins)
2. `hooks.post_prepare` (shell argv; Python via pluggy later)
3. Runtime: IDE/debug profile, secrets
4. `hooks.pre_up`
5. `docker compose up`

### Container contract

`ContainerConfig` v1 in the container is unchanged (stdlib validation, no new PyPI deps in images).

## Compatibility rules (manager 4.4)

Implemented in [dev_project/manifest/compat.py](../../dev_project/manifest/compat.py):

1. **v1:** `manifest_schema` absent → schema 1; `odpm_version` must be in supported contract lines.
2. **v2:** `requires_odpm` must parse as semver and be ≤ installed manager.
3. **Unsupported `manifest_schema`:** `ConfigError`.

## Consequences

- User-facing version is unified: `RELEASE_VERSION` = `ODPM_VERSION` = pip/deb/`odpm --version` (currently `4.4.3`).
- Existing `odpm_version: "4.0"` v1 projects remain supported; manifest contract line is unchanged.
- Factory and fixtures use `MANIFEST_V1_CONTRACT_LINE` for new flat `odpm_version`, not `RELEASE_VERSION`.
- Follow-up epics: C-8…C-10, manifest reader/schemas, migrator CLI, extensions registry, compose fragments.

## References

- [goals_ru.md](../../goals_ru.md) — north star manifest and plugins
- [packaging.md](packaging.md) — version axes for releases
- [roadmap 4.4](.cursor/plans/roadmap_4.4_97c7eb68.plan.md) (local)
