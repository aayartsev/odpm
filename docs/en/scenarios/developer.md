# Developer scenario (`developer`)

> **AI-translated** from Russian.

The **`ODPM_SCENARIO=developer`** variable is **local development** mode on your own computer. This is the default value.

## Purpose

The developer writes module code, debugs it in the editor, frequently restarts module updates, and uses Odoo development mode (auto-reload and related features). Platform and addon sources are **mounted from the host disk** into the container — changes on disk are immediately visible to the Odoo process (subject to reload policy).

## Environment behavior

| Area | How it works |
|------|--------------|
| **Debugger** | `ODPM_DEBUGGER_BACKEND` mode: `debugpy_listen` (container listens, VS Code / PyCharm Attach) or `pydevd_connect` (PyCharm Debug Server). Port `DEBUGGER_PORT` — see [IDE debugging](../operations/vscode-debug.md). |
| **Module secrets** | Optional: `.odpm/secrets.json` → mount `/run/odpm/secrets.json` — [local secrets](../operations/secrets.md). |
| **PostgreSQL** | Database port is available on the host (not only on the loopback interface) — convenient for local utilities. Cluster state and drift: [database-state.md](../reference/database-state.md). |
| **Sources** | Platform directories, the project under development, and dependencies are mounted from the developer's computer. |
| **Python environment** | "Recreatable" mode: when the version lock file changes, the environment may be rebuilt. |
| **Python warnings in logs** | `docker-compose` sets `PYTHONWARNINGS=ignore::DeprecationWarning:docutils` so that Odoo startup does not scare beginners with a long traceback from deprecated API in the **docutils** package (this is not an error in your code). In `server` and `ci` scenarios the filter is **not** enabled — warnings remain in the log and may signal docutils incompatibility with the Python version in the image. |
| **CI image build** | The `--build-image` command is **unavailable** (only in the `ci` scenario). |

## Odoo development mode (`dev_mode`)

In `user_settings.json`, the **`dev_mode`** field sets Odoo `--dev` flags (e.g. `reload`, `xml`, `all` — see Odoo documentation). Works **only** in this scenario. With `reload` or `all` values, odpm adds the `inotify` package to Python requirements for code auto-reload.

After changing `dev_mode`, recreate compose: `odpm --skip-start`.

## Typical day

1. `odpm` — prepare and start containers.
2. `odpm -d dev_db -u` — update modules after changes.
3. Debugger in VS Code — as needed.
4. `http://127.0.0.1:8069` — check in the browser.

Manual scenarios (plan, drift, debugging) on demo wrappers: [demo-projects](https://github.com/aayartsev/odpm/blob/4.4-dev/docs/contributing/demo-projects.md).

After changing `POSTGRES_SERVICE_NAME` or the port in `.env` — run `odpm database status` and `odpm plan --skip-start` before a full restart.

## Switching to another scenario

1. Change `ODPM_SCENARIO` in the **project directory** `.env` (it takes precedence over the file in `~/.odpm/`).
2. Run `odpm --skip-start`.
3. Restart containers: `docker compose up -d` or `odpm` again.

Scenario comparison: [scaling](scaling.md).
