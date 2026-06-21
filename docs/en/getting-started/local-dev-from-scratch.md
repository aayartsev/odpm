# Local dev from scratch

> **AI-translated** from Russian.

Typical path for a **developer** on their own machine. Usage scenario: **`ODPM_SCENARIO=developer`** (default).

## Why a separate directory per Odoo version

Create a disk folder for the project **environment**, not necessarily only module sources. A version suffix helps, e.g. `my-odoo-project-19`: major versions differ enough that 18.0 and 19.0 deserve **separate** odpm directories even when modules share one git repo.

```bash
mkdir my-odoo-project-19
cd my-odoo-project-19
```

odpm fills this folder with service files (`docker-compose.yml`, `user_settings.json`, `.odpm/`, etc.). Your **developing project** (modules) may live elsewhere or in another repo — odpm links it during init.

## Editor and terminal

Open the folder in **Visual Studio Code** (File → Open Folder). The integrated terminal is convenient for odpm commands.

**Important:** do not run `odpm` inside a host Python venv. Use system `python3` or the `odpm` package command; Odoo’s isolated Python env is created **inside the container**.

## Init from a git repository

```bash
odpm --init https://github.com/your-org/your-odoo-project.git --branch 19.0
```

`--branch` is the **developing** repository branch. If omitted, the git server’s default branch is used.

## Init from a local directory

If you are not using remote git yet:

```bash
odpm --init file:///home/user/path/to/my_addons
```

See [Git repository links](../reference/git-links.md) for `file://` and the three slashes.

## What happens on first run

On first `odpm --init` (and on full prepare runs), odpm:

1. Runs the setup wizard and saves answers to `.env` (backup dir, git clone dir, ports, **scenario** `developer` / `server` / `ci`).
2. When deploying from scratch, asks for Odoo version if missing from the developing project’s `odpm.json`.
3. Clones the Odoo **platform** repo (can take **40+ minutes** — be patient).
4. Clones the developing project or links the local path you gave.
5. Generates `Dockerfile` for the chosen Linux distro and Python version.
6. Copies the template to `.odpm/dockerignore` and creates the root `.dockerignore` for image builds.
7. Builds the base Docker image when needed.
8. Generates `docker-compose.yml`.
9. In developer scenario — creates VS Code debugger settings.
10. Starts containers (`docker compose up`), installs Python deps in the container venv, and starts Odoo.

Stop a foreground interactive run: **Ctrl+C**. Stop containers separately if needed: `docker compose down`.

## First database and modules

After a successful prepare:

```bash
odpm -d test_db -i -u
```

- `-d test_db` — database name; created with `db_creation_data` from `user_settings.json` if missing.
- `-i` — install modules from `init_modules`.
- `-u` — update modules from `update_modules`.

Open `http://127.0.0.1:8069` — Odoo login should appear.

## Two main config files

| File | Role |
|------|------|
| **`odpm.json`** | **Stack** manifest: Odoo/Python/PostgreSQL versions, git dependencies, Python packages. Often in git with modules. |
| **`user_settings.json`** | **Workflow**: developing project link, modules to install/update, DB creation params, Odoo dev mode. Created from template if missing. |

More detail: [odpm.json and user_settings.json](../reference/config-split.md).

## Day-to-day tasks

| Task | Action |
|------|--------|
| Restart after config changes | `odpm` or `odpm --skip-start`, then `docker compose up -d` if needed |
| Update module after code change | `odpm -d test_db -u` |
| Database backup | `odpm -d test_db --db-backup` |
| Restore from archive | `odpm -d test_db --db-restore archive_name` |
| New module scaffold | `odpm scaffold module_name` |
| Breakpoint debugging | [IDE debugging](../operations/vscode-debug.md) |
| Module API keys / tokens | [Local secrets](../operations/secrets.md) — `.odpm/secrets.json` → `/run/odpm/secrets.json` |

## Module secrets (optional)

If modules call external APIs, prepare secrets **before or after** init:

```bash
# from template (after odpm --init)
cp .odpm/secrets.example.json .odpm/secrets.json
# edit keys, then:
odpm --skip-start
```

Or at init: `odpm --init … --secrets-file /path/to/secrets.json`.

After value changes, run `odpm --skip-start` and `docker compose up -d` if needed. See [local secrets](../operations/secrets.md).

## `.dockerignore` template

Edit exclusion rules in **`.odpm/dockerignore`**. odpm recreates the root `.dockerignore` on each run — do not edit it by hand. To reset the template, delete `.odpm/dockerignore` and run odpm again.
