# ADR-004: Plugin API stability (4.5)

**Status:** accepted (4.5-dev)  
**Date:** 2026-06-22

## Context

odpm 4.4 introduced pluggy entry points (`odpm.prepare_steps`, `odpm.hooks`), manifest v2 `services` / `hooks`, and frozen `ExtensionHostContext`. Third-party packages had no explicit API version, making breaking changes hard to communicate.

Phase P (Plugins 2.0) adds project-local plugins, plan integration, and additional lifecycle hooks (`post_clone`).

## Decision

### API version constant

- `dev_project/extensions/api.py` exports **`EXTENSION_API_VERSION = "1.0"`**.
- Plugin packages should declare compatibility in documentation and optionally call `assert_extension_api_compatible()` at import time.
- odpm host code does **not** read version from `pyproject.toml` automatically in 4.5.0; enforcement is contract tests + maintainer review.

### Semver policy

| Change type | API bump |
|-------------|----------|
| New optional hook method (e.g. `run_post_clone`) with host `hasattr` fallback | **Minor** (same `EXTENSION_API_VERSION`) |
| New required protocol method, renamed entry-point group, removed hook phase | **Major** (`EXTENSION_API_VERSION` → `2.0`) |
| New manifest hook phase with schema + plan step | **Minor** when old manifests remain valid |
| New prepare-step `order` semantics or conflicting id rules | **Major** |

Breaking changes ship only with a major `EXTENSION_API_VERSION` bump and release notes; manager keeps reading older plugins when possible via optional protocol methods.

### Stable surfaces (1.0)

- Entry-point groups: `odpm.prepare_steps`, `odpm.hooks`
- Registry helpers: `register_prepare_step`, `register_compose_fragment`, `register_hook_runner`
- Types: `ExtensionHostContext`, `PrepareStepPlugin`, `ComposeFragmentPlugin`, `HookRunner`
- Manifest v2: `services`, `hooks.post_prepare`, `hooks.pre_up`, `hooks.post_clone`, `extensions.local`
- Lifecycle order: prepare steps → `post_clone` (after git materialize) → … → `post_prepare` → runtime → `pre_up` → compose up

### Project-local plugins

- Code loaded only from `{project_dir}/.odpm/plugins/` (no arbitrary paths).
- Optional manifest allow-list: `extensions.local` (module basenames).
- Security: path traversal rejected; see `extensions/local.py`.

## Consequences

- Contract suite includes `tests/fixtures/sample_plugin/` loaded in `test_manifest_contract.py`.
- `docs/reference/plugins.md` documents `EXTENSION_API_VERSION` and lifecycle order.
- Future removals require ADR update and major API version.
