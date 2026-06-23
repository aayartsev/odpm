# ADR-004: Plugin API stability (4.5)

**Status:** accepted (4.5-dev). **Amended** for 4.6 debt closure slice D4 (API 1.1).  
**Date:** 2026-06-22

## Context

odpm 4.4 introduced pluggy entry points (`odpm.prepare_steps`, `odpm.hooks`), manifest v2 `services` / `hooks`, and frozen `ExtensionHostContext`. Third-party packages had no explicit API version, making breaking changes hard to communicate.

Phase P (Plugins 2.0) adds project-local plugins, plan integration, and additional lifecycle hooks (`post_clone`).

## Decision

### API version constant

- `dev_project/extensions/api.py` exports **`EXTENSION_API_VERSION = "1.1"`** (4.6+).
- **`SUPPORTED_EXTENSION_API_VERSIONS`**: `1.0`, `1.1` — plugins without `EXTENSION_API_VERSION` are treated as **1.0**.
- Host validates plugins at load time via `validate_plugin_api()` (`extensions/loader.py`) for setuptools entry points and `.odpm/plugins/*.py`.
- Plugin packages should declare `EXTENSION_API_VERSION` and may call `assert_extension_api_compatible()` at import time.
- odpm host does **not** read version from `pyproject.toml` automatically; enforcement is load-time check + contract tests.

### 4.6 amendment (D4 / API 1.1)

| Addition | Notes |
|----------|-------|
| Load-time API check | `validate_pluggy_manager_plugins()` after entry-point load; local plugins after `exec_module` |
| `compose_service_patches(ctx)` | Optional on `ComposeFragmentPlugin`; merged after manifest `service_patches` |
| Nested dep compose inherit | v2 `services` / `service_patches` from dependency `odpm.json` merged in `apply_transitive_requirements`; **host manifest wins** on name conflict |
| `sample_plugin` | Contract fixture for sidecar + `service_patches` |

### Semver policy

| Change type | API bump |
|-------------|----------|
| New optional hook method (e.g. `run_post_clone`) with host `hasattr` fallback | **Minor** (same `EXTENSION_API_VERSION`) |
| New required protocol method, renamed entry-point group, removed hook phase | **Major** (`EXTENSION_API_VERSION` → `2.0`) |
| New manifest hook phase with schema + plan step | **Minor** when old manifests remain valid |
| New prepare-step `order` semantics or conflicting id rules | **Major** |

Breaking changes ship only with a major `EXTENSION_API_VERSION` bump and release notes; manager keeps reading older plugins when possible via optional protocol methods.

### Stable surfaces (1.0 / 1.1)

- Entry-point groups: `odpm.prepare_steps`, `odpm.hooks`
- Registry helpers: `register_prepare_step`, `register_compose_fragment`, `register_hook_runner`
- Types: `ExtensionHostContext`, `PrepareStepPlugin`, `ComposeFragmentPlugin`, `HookRunner`
- Manifest v2: `services`, `service_patches`, `hooks.post_prepare`, `hooks.pre_up`, `hooks.post_clone`, `extensions.local`
- Compose plugins (1.1): optional `compose_service_patches()` alongside `compose_services()`
- Lifecycle order: prepare steps → `post_clone` (after git materialize) → … → `post_prepare` → runtime → `pre_up` → compose up

### Project-local plugins

- Code loaded only from `{project_dir}/.odpm/plugins/` (no arbitrary paths).
- Optional manifest allow-list: `extensions.local` (module basenames).
- Security: path traversal rejected; see `extensions/local.py`.

## Consequences

- Contract suite includes `tests/fixtures/sample_plugin/` loaded in `test_manifest_contract.py`.
- `docs/reference/plugins.md` documents `EXTENSION_API_VERSION` and lifecycle order.
- Future removals require ADR update and major API version.
