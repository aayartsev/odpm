# odpm plugins and extensions (4.4+)

> **AI-translated** from Russian.

odpm 4.4+ adds a host **extension API**: prepare steps, compose fragments, and lifecycle hooks. Plugins do not get direct access to mutable `Config` — only frozen [`ExtensionHostContext`](https://github.com/aayartsev/odpm/blob/4.4-dev/dev_project/extensions/context.py).

## Extension API version (4.6+)

Current API: **`EXTENSION_API_VERSION = "1.1"`** (`dev_project/extensions/api.py`). Supported: **1.0**, **1.1**; modules without `EXTENSION_API_VERSION` are treated as **1.0**. The host validates version when loading entry points and `.odpm/plugins/*.py`. In your plugin:

```python
from dev_project.extensions.api import EXTENSION_API_VERSION, assert_extension_api_compatible

assert_extension_api_compatible(EXTENSION_API_VERSION)
```

Breaking changes to pluggy protocols or manifest hooks require a major API bump. Policy: [ADR-004](https://github.com/aayartsev/odpm/blob/4.6.0-dev/docs/contributing/adr-004-plugin-api-stability.md).

## Three ways to extend a project

| Mechanism | Declared in | When it runs |
|-----------|-------------|--------------|
| **Manifest `services`** | `odpm.json` v2 → `services` | Prepare `compose.fragments`; plan `compose.fragment.<name>` |
| **Manifest `hooks`** | `odpm.json` v2 → `hooks` | `post_clone` after git materialize; `post_prepare` after prepare; `pre_up` before compose up |
| **Python entry points** | package `pyproject.toml` | Pluggy: `odpm.prepare_steps`, `odpm.hooks`; secrets: `odpm.secrets_providers` |
| **Project-local plugins** | `.odpm/plugins/*.py` or `extensions.local` | Loaded at bootstrap (sandboxed to project dir) |

v2 field details: [odpm.json](odpm-json.md). ADR: [adr-001-extensions-and-manifest-v2.md](https://github.com/aayartsev/odpm/blob/4.6.0-dev/docs/contributing/adr-001-extensions-and-manifest-v2.md).

## Declarative service (Mailpit)

Test SMTP with web UI on port **8025**. Add to nested manifest v2:

```json
{
  "manifest_schema": 2,
  "requires_odpm": "4.6.0",
  "services": {
    "mailpit": {
      "image": "axllent/mailpit",
      "restart": "unless-stopped",
      "ports": ["8025:8025", "1025:1025"]
    }
  }
}
```

Sidecars may set **`user`**, **`tty`**, **`hostname`**, **`healthcheck`**, **`privileged`**, and **`pid`** (same as `service_patches`). For **git build contexts** (recommended, 4.7+), use `service_sources` and `${@source:...}`; for sidecar API keys use `${@secret:...}` from `.odpm/secrets.json`:

```json
"service_sources": {
  "autoparts_env": "https://github.com/org/autoparts-env.git 17.0"
},
"services": {
  "armtek_test": {
    "source": "autoparts_env",
    "image": "autoparts_env:emulator",
    "user": "root",
    "tty": true,
    "volumes": ["${@source:autoparts_env}/data:/data:Z"],
    "environment": {
      "APILOGIN": "${@secret:partner_armtek.armtek.apilogin}"
    }
  }
}
```

`${@secret:...}` requires `.odpm/secrets.json` or `--secrets-file`; the value lands in generated compose YAML intentionally. See [secrets.md](../operations/secrets.md). See also [service-sources.md](service-sources.md). Legacy path from `.env`:

```json
"services": {
  "armtek_test": {
    "image": "autoparts_env:emulator",
    "user": "root",
    "tty": true,
    "volumes": ["${DIGITAL_AUTOPARTS_ENV_DIR}/data:/data:Z"]
  }
}
```

Same spec in code: `dev_project.extensions.reference.mailpit.MAILPIT_SERVICE_SPEC`.

After `odpm up` the service appears in generated `docker-compose.yml` (`{COMPOSE_SERVICE_FRAGMENTS}` block). Materialize artifacts: `.odpm/compose/fragments/mailpit.yml` (gitignored).

In sidecar `depends_on`, use the **logical** name `db` (not physical `acme-db`); with `ODPM_COMPOSE_PREFIX` odpm rewrites dependencies at compose generation — see [env-dotenv.md](env-dotenv.md).

### Compose network (`networks`, 4.7+)

By default the stack uses Docker Compose implicit default network. To attach **all** services to one named network, set in `.env`:

```ini
ODPM_COMPOSE_NETWORK=stack
```

For an **external** reverse-proxy network (Traefik, Caddy), typically in `~/.odpm/.env`:

```ini
ODPM_COMPOSE_NETWORK=proxy
ODPM_COMPOSE_NETWORK_EXTERNAL=1
```

See [env-dotenv.md](env-dotenv.md), [ADR-014](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-014-compose-stack-network.md).

Sidecars may declare `networks` (logical names; with `ODPM_COMPOSE_PREFIX` odpm rewrites managed networks to physical names; external names stay as-is):

```json
"services": {
  "metrics": {
    "image": "prom/prometheus",
    "networks": ["stack"]
  }
}
```

If manifest uses `networks: ["stack"]`, `.env` must set **`ODPM_COMPOSE_NETWORK=stack`** (or omit `networks` — odpm attaches the sidecar automatically). `odpm manifest validate` logs a **warning** when logical `stack` does not match `.env`.

Proxy-only sidecar with `${VAR}`:

```json
"networks": ["${PROXY_NETWORK}"]
```

with `PROXY_NETWORK=proxy` and `ODPM_COMPOSE_NETWORK=proxy` in `.env`.

### Patch built-in services (`service_patches`, 4.6+)

Names **`odoo`**, **`db`**, **`postgres`** cannot appear in `services` — use patches only. Policy: [ADR-009](https://github.com/aayartsev/odpm/blob/4.6.0-dev/docs/contributing/adr-009-compose-service-patch.md).

```json
"service_patches": {
  "odoo": {
    "environment": {
      "CUSTOM_METRIC": "1"
    }
  }
}
```

`odpm plan` shows `compose.patch.odoo` (preview); patches apply at `compose.generate`.

### `command` / `entrypoint` for sidecars (4.6+)

**Exec form only** (JSON string array) in `services.<name>`:

```json
"services": {
  "worker": {
    "image": "busybox:latest",
    "command": ["sh", "-c", "sleep infinity"]
  }
}
```

The `odoo` start command stays owned by the generator; override via `service_patches.odoo.command` only when explicitly needed.

## Lifecycle hooks in manifest

```json
"hooks": {
  "post_clone": [
    ["./scripts/after-clone.sh"]
  ],
  "post_prepare": [
    ["./scripts/notify.sh", "prepare-done"],
    "mycompany.odpm.hooks.warmup"
  ],
  "pre_up": [
    ["docker", "network", "create", "odpm-dev", "||", "true"]
  ]
}
```

Each element is either **argv** (string array, runs in `project_dir` **without a shell**) or a **plugin id** (string) for the pluggy hook runner.

Argv supports **`${VAR}`** / **`${VAR:-default}`**, **`${@source:<name>}`** (after `sources.materialize`), and **`${@secret:<key>}`** (from `.odpm/secrets.json`): expanded at hook execution. The subprocess receives **merged env** (process + missing keys from `.env`). Example sidecar image build:

```json
"hooks": {
  "post_prepare": [[
    "docker", "build",
    "-f", "${@source:autoparts_env}/Dockerfile",
    "-t", "autoparts_env:emulator",
    "${@source:autoparts_env}"
  ]]
}
```

`services` / `service_patches` use the same substitution rules for string fields (`image`, `volumes[]`, `command[]`, `environment`, …): `${VAR}` / `${@secret:...}` at manifest read; `${@source:...}` after `sources.materialize`.

Prepare order (excerpt):

1. Git materialize
2. **`sources.materialize`** (when `service_sources` is set)
3. `hooks.post_clone` (if configured)
4. All prepare steps (built-in + `odpm.prepare_steps` + local plugins), sorted by `order`
5. `hooks.post_prepare`
6. Runtime: debug profile, IDE, database drift
7. `hooks.pre_up`
8. `docker compose up`

`odpm plan` shows `hooks.*`, `compose.fragment.<service>`, and `compose.patch.<service>` steps when configured.

### Prepare step `order` field

Lower `order` runs earlier among **extension** steps (built-in order is fixed in the registry). Conflicting `id` with a built-in step → `ValueError` on registration.

Shell hook failure → `PipelineError` with the command exit code.

## Python plugin: compose fragment

```python
# my_odpm_mailpit/__init__.py
from dev_project.extensions import ExtensionHostContext, register_compose_fragment
from dev_project.extensions.reference.mailpit import MAILPIT_SERVICE_SPEC

class MailpitFragment:
    name = "mailpit"

    def compose_services(self, ctx: ExtensionHostContext) -> dict:
        return {"mailpit": dict(MAILPIT_SERVICE_SPEC)}

def _register():
    register_compose_fragment("mailpit", MailpitFragment())
```

Register on package import or via entry point (see below).

### Patch built-in services from Python (API 1.1+)

Optional `compose_service_patches` on a compose fragment (same rules as manifest `service_patches`):

```python
def compose_service_patches(self, ctx: ExtensionHostContext) -> dict:
    return {"odoo": {"environment": {"MY_FLAG": "1"}}}
```

### Nested dependency `services` (4.6+)

With `use_oca_dependencies`, v2 `services` / `service_patches` from dependency `odpm.json` files are inherited into host compose after `project.map_folders`. On name conflict the **host manifest wins**. See [ADR-004](https://github.com/aayartsev/odpm/blob/4.6.0-dev/docs/contributing/adr-004-plugin-api-stability.md).

## Python plugin: prepare step

```toml
[project.entry-points."odpm.prepare_steps"]
my_step = "my_odpm_plugin.steps:plugin_factory"
```

```python
from dataclasses import dataclass
from dev_project.prepare.helpers import make_plan_step
from dev_project.prepare.types import PrepareContext

@dataclass(frozen=True)
class MyPrepareStep:
    id: str = "mycompany.custom.step"
    description: str = "Custom prepare work"
    order: int = 500

    def evaluate(self, ctx: PrepareContext):
        return make_plan_step(self.id, self.description, "run", True, "always run")

    def execute(self, ctx: PrepareContext) -> None:
        ...

def plugin_factory():
    return MyPrepareStep()
```

`evaluate` must be **side-effect free** — `odpm plan` calls only evaluate.

## Python plugin: lifecycle hook runner

```toml
[project.entry-points."odpm.hooks"]
warmup = "my_odpm_plugin.hooks:WarmupRunner"
```

```python
class WarmupRunner:
    name = "mycompany.odpm.hooks.warmup"

    def run_post_clone(self, ctx) -> None:
        ...

    def run_post_prepare(self, ctx) -> None:
        ...

    def run_pre_up(self, ctx) -> None:
        ...
```

Id in manifest (`"mycompany.odpm.hooks.warmup"`) must match runner `name`.

## Example package `pyproject.toml`

```toml
[project]
name = "odpm-services-mailpit"
version = "0.1.0"
dependencies = ["odpm>=4.4"]

[project.entry-points."odpm.hooks"]
# optional lifecycle runners

[project.entry-points."odpm.prepare_steps"]
# optional prepare steps
```

Install the package in the host venv (`pip install -e .`) next to odpm.

## Project-local plugins (4.5+)

Without a separate pip package, place modules under **`.odpm/plugins/`** in the project (this directory only; no `..` in module names). Optional allow-list in manifest v2:

```json
"extensions": {
  "local": ["mailpit_local"]
}
```

Loads `project_dir/.odpm/plugins/mailpit_local.py`. Example fixture: `tests/fixtures/sample_plugin/`.

## Cookbook (minimal plugin)

1. Manifest v2 `services.mailpit` **or** `register_compose_fragment` in Python.
2. Prepare step with side-effect-free `evaluate` + `execute` for file writes.
3. Hook runner with `name` matching the id in `hooks.post_prepare`.
4. `pip install -e .` or `.odpm/plugins/my_plugin.py`.
5. Run `odpm plan` — verify `compose.fragment.*`, `hooks.*`, and extension prepare steps.

Template `pyproject.toml`: `tests/fixtures/sample_plugin/pyproject.toml`.

## Limitations

- Container-side `ContainerConfig` stays **stdlib-only** (no new PyPI deps in the image).
- Compose YAML is generated by the host engine `dev_project/yaml/` (ruamel.yaml); YAML anchors/merge aliases are not supported.
- Name conflict: plugin compose fragment **overwrites** a same-named service from manifest.

## See also

- [Generated files](generated-files.md) — `.odpm/compose/fragments/`
- Declarative sidecar services — **Mailpit** section above and the extension mechanisms table
- Deprecated drafts in `dev_project/plugins/` (`services_ru.md`, `todo_ru.md`) — redirect here
