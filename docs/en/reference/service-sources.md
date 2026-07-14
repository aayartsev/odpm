# Service sources (git sidecar / build contexts)

> **AI-translated** from Russian.

The **`service_sources`** block in manifest v2 describes **external git repositories** for sidecar services and `docker build` hooks — without manual absolute paths in `.env`.

See also: [odpm.json](odpm-json.md), [repository links](git-links.md), [plugins](plugins.md), [deps.lock](deps-lock.md).

## Model

| Element | Rule |
|---------|------|
| `service_sources.<name>` | git link (same syntax as `dependencies` / `platform.git`) |
| Name `<name>` | `[a-z][a-z0-9_]*` |
| `services.<svc>.source` | optional reference to a name from effective `service_sources` |
| `${@source:<name>}` | path after materialize (env `ODPM_SOURCE_<NAME>`) |
| `file://` | local override without clone |

Repositories from `service_sources` are **not** added to `dependencies` and **not** included in `addons_path`.

## Manifest example

```json
{
  "manifest_schema": 2,
  "requires_odpm": "4.7.0",
  "service_sources": {
    "autoparts_env": "https://github.com/org/autoparts-env.git 17.0"
  },
  "services": {
    "armtek_test": {
      "source": "autoparts_env",
      "image": "autoparts_env:emulator",
      "user": "root",
      "tty": true,
      "volumes": ["${@source:autoparts_env}/data:/data:Z"]
    }
  },
  "hooks": {
    "post_prepare": [
      [
        "docker", "build",
        "-f", "${@source:autoparts_env}/Dockerfile",
        "-t", "autoparts_env:emulator",
        "${@source:autoparts_env}"
      ]
    ]
  }
}
```

Project `.env` only needs standard odpm variables; **`DIGITAL_AUTOPARTS_ENV_DIR` is not required**.

## Materialize

Prepare step **`sources.materialize`** (after `git.materialize`, before `hooks.post_clone`):

1. Clones git sources under **`${ODOO_PROJECTS_DIR}/service-sources/<name>`**
2. For `file://` — uses the given directory (no clone)
3. Writes paths to `ODPM_SOURCE_*` and **re-expands** `services` / `service_patches` before compose

With `--no-git-update`, odpm only verifies that directories already exist.

## `${@source:...}` substitution

- Syntax: **`${@source:<name>}`** → env key **`ODPM_SOURCE_<NAME>`** (uppercase name)
- On manifest read, unresolved `${@source:...}` in compose fields **does not fail**; paths are injected after `sources.materialize`
- Hooks expand `${@source:...}` at execution time (when the resolver already holds paths)
- The `source` field on `services.*` is **stripped** from generated compose YAML

Backward compatibility: legacy `${DIGITAL_AUTOPARTS_ENV_DIR}` from `.env` still works.

## Scenario overlays

In `scenarios.*`, `service_sources` merges **replace-by-name** (overlay overrides the same name).

## deps.lock

In `.odpm/deps.lock.json` (schema v1):

```json
"service_sources": {
  "autoparts_env": {
    "url": "https://github.com/org/autoparts-env",
    "commit": "…",
    "branch": "17.0"
  }
}
```

- `odpm --update-lock` collects pins after materialize
- CI (strict) verifies drift by source name

## Validation

`odpm manifest validate`:

- `service_sources` keys — JSON Schema + name regex
- `services.*.source` — must exist in effective `service_sources`
