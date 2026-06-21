# Generated files

> **AI-translated** from Russian.

Some files in the project directory are **created and updated by odpm**. Do not edit them manually: on the next run changes will be lost or will drift from the description in `odpm.json`.

| File | How to update |
|------|---------------|
| `docker-compose.yml` | `odpm` or `odpm --skip-start` |
| root `.dockerignore` | from `.odpm/dockerignore` template; reset template — delete `.odpm/dockerignore` and run odpm again |
| `.odpm/runtime/config.json` | automatically; in project gitignore |
| `.odpm/database/last_run.json` | on adoption and after successful checker; mounted in container; see [database-state.md](database-state.md) |
| `.odpm/runtime/debug-profile.json` | automatically in `developer` scenario (`include_debugpy`); in gitignore |
| `.odpm/secrets.example.json` | template on init; in git |
| `.odpm/secrets.json` | manually or `--secrets-file`; in `.odpm/.gitignore` |
| `.odpm/runtime/secrets.json` | step `secrets.materialize`; mounted in container; in gitignore; see [secrets](../operations/secrets.md) |
| `.vscode/launch.json`, `.vscode/settings.json` | `odpm --skip-start` when `ODPM_IDE=vscode` or `both` and `ODPM_DEBUGGER_BACKEND=debugpy_listen`; `settings.json` includes `python.analysis.extraPaths` for platform, developing, and dependencies |
| `.run/Odoo Remote Attach.run.xml` | `odpm --skip-start` when `ODPM_IDE=pycharm` or `both` and **`debugpy_listen`** (PyCharm Attach to DAP) |
| `.run/Odoo Debug Server.run.xml` | `odpm --skip-start` when `ODPM_IDE=pycharm` or `both` and **`pydevd_connect`** (PyCharm Debug Server, Pro) |

When `ODPM_DEBUGGER_BACKEND` changes, odpm removes the obsolete odpm file from the pair above (user `.run/*.run.xml` files are untouched). See [IDE debugging](../operations/vscode-debug.md).

## Exception: Odoo configuration

File **`odoo.conf`** (or `{platform_name}.conf`) is **edited by the user**, but odpm recalculates addon paths and data directory for the container on prepare. See [odoo.conf](odoo-conf.md).

## Why it works this way

Manual editing of `docker-compose.yml` breaks the **single contract** between host and container (ports, entrypoint, configuration handoff). odpm generates compose from scenario and command-line parameters so developer, administrator, and build stay on one project description.

After an odpm version upgrade or `ODPM_SCENARIO` change, run **`odpm --skip-start`** and restart containers.
