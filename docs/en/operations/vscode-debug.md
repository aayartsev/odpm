# Debugging in the IDE (VS Code, PyCharm)

> **AI-translated** from Russian.

Breakpoint debugging is available in the **`developer`** scenario. The mode is set by **`ODPM_DEBUGGER_BACKEND`** in `.env` (see [env-dotenv](../reference/env-dotenv.md)).

Hands-on attach on a demo wrapper (`$ODPM_DEMO_19`): [demo-projects § S5](https://github.com/aayartsev/odpm/blob/4.4-dev/docs/contributing/demo-projects.md#s5--отладка-в-vs-code).

When this doc mentions VS Code, it applies to all derivatives that support the same debugging mechanism.

## Two modes (backends)

| Backend | Who listens on the port | IDE | Compose |
|---------|-------------------------|-----|---------|
| **`debugpy_listen`** (default) | container (`debugpy --listen`) | VS Code, PyCharm **Attach to DAP** | publish `DEBUGGER_PORT:DEBUGGER_PORT` |
| **`pydevd_connect`** | **IDE** (PyCharm Debug Server on the host) | **PyCharm Professional only** | `extra_hosts: host.docker.internal:host-gateway`, **no** debugger port publish |

The meaning of **`DEBUGGER_PORT`** depends on the backend:

- **`debugpy_listen`** — port **inside the container**, forwarded to `localhost` on the host (attach from the IDE).
- **`pydevd_connect`** — port of the **Debug Server on the host** (PyCharm listens on `localhost:DEBUGGER_PORT`; the container connects to `ODPM_DEBUGGER_CONNECT_HOST`).

## What odpm configures

- The debugger package is installed in the container venv: **`debugpy`** or **`pydevd-pycharm`** (pinned in `dev_project/constants/core.py`; when the backend changes, the unused package is removed from requirements).
- In **`.odpm/runtime/config.json`** — a `debugger` object (backend, port, connect_host, suspend_on_connect). Fields `connect_host` and `suspend_on_connect` are always written; for `debugpy_listen` the runtime **does not use** them.
- In **`.odpm/runtime/debug-profile.json`** — an IDE-neutral profile (`schema_version: 2`): `backend`, `direction`, `protocol`, host/port, `path_mappings`.
- By **`ODPM_IDE`**: `vscode` / `both` → `.vscode/`; `pycharm` / `both` → `.run/*.run.xml` (which file depends on the backend); `none` — only `debug-profile.json` is created.

Regeneration: `odpm` or `odpm --skip-start`. Plan steps: `ide.debug_profile`, `pycharm.settings`; diff — `odpm plan --plan-show-diff`.

---

## `debugpy_listen` — VS Code / PyCharm Attach to DAP

### Profile (example)

```json
{
    "schema_version": 2,
    "debugger": {
        "backend": "debugpy_listen",
        "direction": "attach",
        "protocol": "debugpy",
        "host": "localhost",
        "port": 5678,
        "name": "Odoo: Remote Attach"
    },
    "path_mappings": [
        { "local": "/abs/path/on/host/odoo", "remote": "/home/odoo/odoo" }
    ]
}
```

### Workflow (VS Code)

1. `.env`: `ODPM_DEBUGGER_BACKEND=debugpy_listen`, `ODPM_IDE=vscode` (or `both`).
2. `odpm` — Odoo in the container listens on the debugger port.
3. In VS Code: Run and Debug → attach to the odpm configuration.
4. Set breakpoints in modules.

### PyCharm Attach to DAP

With `ODPM_IDE=pycharm` or `both` and **`debugpy_listen`**, odpm creates **`.run/Odoo Remote Attach.run.xml`** (Attach to DAP, PyCharm 2024+).

1. Start Odoo via odpm.
2. In PyCharm, connect to **Odoo: Remote Attach**.

**PyCharm Community Edition** does not support remote debug in this mode — use VS Code or PyCharm Professional.

---

## `pydevd_connect` — PyCharm Debug Server (Pro)

The container **connects to the IDE**, not the other way around. Requires **PyCharm Professional** (Debug Server).

### `.env` setup

```ini
ODPM_DEBUGGER_BACKEND=pydevd_connect
ODPM_IDE=pycharm
DEBUGGER_PORT=5678
ODPM_DEBUGGER_CONNECT_HOST=host.docker.internal
ODPM_DEBUGGER_SUSPEND=1
```

- **`ODPM_IDE=vscode`** with `pydevd_connect` — incompatible (odpm emits a warning); use `pycharm` or `both`.
- **`ODPM_IDE=none`** — no XML is generated (warning); for Debug Server you need `pycharm` / `both`.

The interactive wizard in `developer` asks for `connect_host` and `suspend` only when `pydevd_connect` is selected.

### Workflow (step order matters)

1. `odpm --skip-start` — the directive updates `docker-compose.yml`, `config.json`, **`.run/Odoo Debug Server.run.xml`**.
2. In PyCharm: **Run** (not Attach) the **Odoo Debug Server** configuration — in the Debug window: *Waiting for process connection...*
3. `odpm` or `docker compose up` — the container calls `pydevd_pycharm.settrace(connect_host, port, suspend=...)`.
4. With `ODPM_DEBUGGER_SUSPEND=1` — in PyCharm press **Resume**, then set breakpoints in addons.

### Compose

- **No** `5678:5678` line in `ports` for the `odoo` service.
- **`extra_hosts: host.docker.internal:host-gateway`** is present (for Linux; on macOS Docker Desktop usually works without manual setup).

### Profile (example)

```json
{
    "schema_version": 2,
    "debugger": {
        "backend": "pydevd_connect",
        "direction": "connect",
        "protocol": "pydevd",
        "host": "localhost",
        "port": 5678,
        "name": "Odoo: Remote Attach"
    },
    "path_mappings": [ ... ]
}
```

`host: localhost` in the profile is the address where the Debug Server **listens on the host** (for PyCharm XML). The container uses `connect_host` from `config.json` (usually `host.docker.internal`).

### Manual connection (other IDEs / TD-FEAT-08b)

For IDEs without an odpm generator, take host/port from `debug-profile.json` and add to the container-side process (after venv bootstrap):

```python
import pydevd_pycharm
pydevd_pycharm.settrace(
    "<connect_host>",
    port=<port>,
    suspend=<True|False>,
    stdout_to_server=True,
    stderr_to_server=True,
)
```

Package: `pydevd-pycharm` (version pinned in odpm, see below).

---

## Switching backend

After changing `ODPM_DEBUGGER_BACKEND`, run `odpm --skip-start` and restart the containers.

When `ODPM_DEBUGGER_BACKEND` changes, odpm on `odpm --skip-start` **removes** the outdated odpm file (`.run/Odoo Remote Attach.run.xml` or `.run/Odoo Debug Server.run.xml`). User configurations in `.run/` are not affected.

When the backend changes, the venv is rebuilt with the required pip package (`debugpy` ↔ `pydevd-pycharm`).

---

## Symbolic links (`create_module_links`)

If **`"create_module_links": true`** is set in `user_settings.json`, odpm creates symlinks to the platform, developing project, and dependencies. This helps align debugger paths: `launch.json` and PyCharm path mappings account for both `~/odoo_projects/...` and paths through the odpm project tree.

The option is **off** by default.

## Imports and code analysis (Pylance / Pyright)

On `odpm --skip-start` (`developer` scenario, `ODPM_IDE=vscode` or `both`), odpm generates `.vscode/settings.json` with **`python.analysis.extraPaths`** from the same repository graph that prepare uses:

- **platform** root (`odoo_src_dir`);
- **developing** project;
- each **git dependency** from `dependencies_projects`;
- **subproject** roots (monorepo with multiple addon directories);
- **venv** `site-packages`.

If the project directory has symlinks (`odoo`, `dependencies/<repo>`), **relative** workspace paths end up in `extraPaths` — more convenient for VS Code.

Limitations:

- **`odoo-stubs`** (`developer` scenario, Odoo ≤ 18) is installed **automatically** in `requirements_txt` — like `debugpy`. Source: [odoo-ide/odoo-stubs](https://github.com/odoo-ide/odoo-stubs) (git dependency; **git** is required on the host for `pip install`). After venv recreation, Pylance picks up stubs from `site-packages` (already in `extraPaths`). For **Odoo ≥ 19** stubs are not added — typing is built into the core.
- Stubs cover the **`odoo` core**, not `odoo.addons.*` (the addons namespace is created at runtime).
- The [vscode-odoo](https://marketplace.visualstudio.com/items?itemName=trinhanhngoc.vscode-odoo) extension already includes its own stubs — duplication is harmless.
- On **server** / **ci**, `odoo-stubs` is removed from `odpm.json` (like debugger packages).
- The file is **overwritten** on every `odpm --skip-start` — do not edit `extraPaths` manually in `.vscode/settings.json`.

---

## Troubleshooting

### `pydevd-pycharm` version and PyCharm

odpm uses **`pydevd-pycharm==243.25659.43`** (aligned with PyCharm **2024.3**). With a different IDE version, connection may fail without an explicit error. Match your PyCharm version or pick a compatible package version in `"requirements_txt"` in `user_settings.json` (advanced scenario).

### Linux: container cannot reach the host

Check that `docker-compose.yml` has `extra_hosts: "host.docker.internal:host-gateway"`. With a custom `ODPM_DEBUGGER_CONNECT_HOST` (host IP), `extra_hosts` may not be added — then specify an IP reachable from the container.

### Odoo starts before Debug Server

Use `ODPM_DEBUGGER_SUSPEND=1` and **first** start Debug Server in PyCharm, **then** the container.

### Verification without a full run (generation)

After `odpm --skip-start` with `pydevd_connect`:

- `config.json`: `"backend": "pydevd_connect"`;
- compose: `extra_hosts`, no `DEBUGGER_PORT:DEBUGGER_PORT`;
- `.run/Odoo Debug Server.run.xml` with `PyRemoteDebugConfigurationType`.

---

## Manual verification checklist (PyCharm Pro)

End-to-end with PyCharm Pro is **not automated** in the repository. Before releasing phase 2, it is recommended to:

- [ ] Run **Odoo Debug Server** → *Waiting for process connection...*
- [ ] `odpm` → container connects
- [ ] Breakpoint in an addon hits
- [ ] `ODPM_DEBUGGER_SUSPEND=1` — Odoo waits for Resume

---

## On server and in CI

In **`server`** and **`ci`** scenarios the debugger is **not used**. Do not enable `developer` on production for debugging.

---

## Other IDEs

| ID | Task | Status |
|----|------|--------|
| TD-FEAT-08a | PyCharm Attach to DAP (`debugpy_listen`) | implemented |
| TD-FEAT-08b | PyCharm Debug Server (`pydevd_connect`) + manual `settrace` for other IDEs | implemented (documentation above) |
