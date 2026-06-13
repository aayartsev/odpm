[![CI](https://github.com/aayartsev/odoo_dev_project/actions/workflows/ci.yml/badge.svg?branch=4.0-beta)](https://github.com/aayartsev/odoo_dev_project/actions/workflows/ci.yml)
[![CI Docker](https://github.com/aayartsev/odoo_dev_project/actions/workflows/ci-docker.yml/badge.svg?branch=4.0-beta)](https://github.com/aayartsev/odoo_dev_project/actions/workflows/ci-docker.yml)
[![Release packages](https://github.com/aayartsev/odoo_dev_project/actions/workflows/release-packages.yml/badge.svg?branch=4.0-beta)](https://github.com/aayartsev/odoo_dev_project/actions/workflows/release-packages.yml)
[![GitHub release](https://img.shields.io/github/v/release/aayartsev/odoo_dev_project?include_prereleases&label=release)](https://github.com/aayartsev/odoo_dev_project/releases)
[![packages](https://img.shields.io/badge/packages-.deb%20%7C%20.rpm-2ea44f?style=flat-square)](https://github.com/aayartsev/odoo_dev_project/releases)

[![ru](https://img.shields.io/badge/lang-ru-green.svg)](README-RU.MD)
[![code AI-assisted](https://img.shields.io/badge/code-AI--assisted-6366F1?style=flat-square)](docs/contributing/README.md#ai-disclosure)
[![AI-assisted docs](https://img.shields.io/badge/docs-AI--assisted-8B5CF6?style=flat-square)](docs/README.md)

# Odoo Developers Project Manager

## Goal of the project
The main goal is - to create tool for developing on odoo platform, which will meet the following requirements:
- do not depend from operating system
- do not depend from process architecture if it is possible (For example you can start this project on MacOS on M1)
- еo transfer all project information, it is enough to have an `odpm.json` in project repository, and the system will be able to easily prepare a new environment in a fully automatic mode based on it.
- To have convenient tools that are often necessary for the developer, for example:
    - fast DB recovery from the archive
    - сreation of a new DB with its own settings (country, language, demo data, etc.)
    - Changing the login and password for the administrator
    - ... and more
    - mechanisms for extending the functionality, for the future

If you are new, follow the step-by-step guide in [`docs/getting-started/local-dev-from-scratch.md`](docs/getting-started/local-dev-from-scratch.md) with your team's repository (it must include `odpm.json`).

## Prepare
You need to download and install the following programs:
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) for Windows and MacOS users
- [git](https://git-scm.com/)
- [python3](https://www.python.org/)
- [Visual Studio Code](https://code.visualstudio.com/)

## Installation

### Debian / Ubuntu (.deb) — recommended on Linux

Download **`odpm_*_all.deb`** from [GitHub Releases](https://github.com/aayartsev/odoo_dev_project/releases) (built by [`.github/workflows/release-packages.yml`](.github/workflows/release-packages.yml) on version tags), from **Actions → Release packages → Artifacts** (`release-packages`) after a push to `4.0-beta` / `4.0-rc1` / `main`, or build locally:

```bash
./scripts/build_deb.sh
sudo apt install ./dist/odpm_*_all.deb
odpm --version
```

The package installs `/usr/bin/odpm` and ships `dev_project` templates + i18n `.mo` under `python3/dist-packages`. **Depends:** `python3 (>= 3.10)`, `python3-packaging`, `git`. **Recommends:** Docker (`docker.io` / `moby-engine`). Zero PyPI runtime dependencies.

Verify checksums from release `SHA256SUMS` when installing from GitHub.

### Fedora / RHEL (.rpm) — recommended on Fedora

Download **`odpm-*.noarch.rpm`** from [GitHub Releases](https://github.com/aayartsev/odoo_dev_project/releases), or build locally (Fedora 41+):

```bash
./scripts/build_rpm.sh
sudo dnf install ./dist/odpm-*.rpm
odpm --version
```

Installs `/usr/bin/odpm` and ships `dev_project` under `python3/site-packages`. **Requires:** `python3-packaging`, `git`. **Recommends:** `moby-engine` / `docker`. Zero PyPI runtime dependencies.

### pip (4.0+)

For development or non-native-package systems. `pip install` uses the **binary distribution** (wheel file `.whl` from a release or a local `python -m build`). Requires **Python 3.10+**. On Linux distros with [PEP 668](https://peps.python.org/pep-0668/) (externally managed system Python), install into a virtual environment or use [pipx](https://pipx.pypa.io/) instead of system-wide `pip install`.

From a clone of this repository:

```bash
pip install /path/to/odoo_dev_project
# editable dev install:
pip install -e /path/to/odoo_dev_project
odpm --version
```

The `odpm` console script uses templates from the installed `dev_project` package (site-packages layout).

### Legacy copy

Copy `odpm.py` and the `dev_project/` directory into your workspace (or clone this repo) and run:

```bash
python3 /path/to/odoo_dev_project/odpm.py --version
```

Both installation modes are supported.

## Host CLI translations (gettext)

Host-facing messages use GNU gettext. Catalog domain `main` lives under `dev_project/i18n/<locale>/LC_MESSAGES/`.

**Which `.env` file is read:** odpm loads **one** file — project `.env` if it exists, otherwise `~/.odpm/.env`. Values are not merged across both files. If project `.env` exists but omits `ODPM_LOCALE`, the key from `~/.odpm/.env` is **not** used; locale falls through to process `ODPM_LOCALE`, then `LANG` / system defaults.

**Locale resolution** inside that file and process environment (first match wins):

| Priority | Source |
|---|---|
| 1 | `ODPM_LOCALE` in the active `.env` file (project or `~/.odpm/`) |
| 2 | `ODPM_LOCALE` in the process environment |
| 3 | `LC_ALL`, `LC_MESSAGES`, or `LANG` (for example `ru_RU.UTF-8`) |
| 4 | System default |
| 5 | `en_US` (catalog fallback) |

Before `OdpmPipeline.setup()`, only **project** `.env` is read for an early locale bootstrap (e.g. sudo guard). Global `~/.odpm/.env` applies after setup when no project `.env` exists.

Leave `ODPM_LOCALE` unset to follow the system/shell locale. For beginners, add to project `.env`:

```ini
ODPM_LOCALE=ru_RU
```

Full Russian translations ship for `ru_RU` only; other locales fall back to English msgids. This is **not** the same as `db_lang` in `user_settings.json` (Odoo database language).

**Three i18n layers:**

| Layer | What is translated | Example |
|---|---|---|
| **A1 — CLI errors & prompts** | Host errors, init prompts, template markers | `Did you install git?` → Russian |
| **A1b — human summaries** | Short host status before/during `compose up` | `Starting containers with Docker Compose...` |
| **Container raw logs** | **English only** (searchable, matches Odoo/PostgreSQL) | `Waiting for PostgreSQL on db:5432` |

Human summaries are emitted from [`dev_project/host_summaries.py`](dev_project/host_summaries.py) on the host. Detailed container output below them stays in English by design.

**Update catalogs after changing `_('...')` strings in `dev_project/`:**

```bash
# 1) Extract msgids from Python sources (optional when editing .po by hand)
xgettext -o dev_project/i18n/main.pot -L Python -k_ dev_project/*.py dev_project/**/*.py

# 2) Merge into locale file (example: Russian)
msgmerge -U dev_project/i18n/ru_RU/LC_MESSAGES/main.po dev_project/i18n/main.pot

# 3) Edit dev_project/i18n/ru_RU/LC_MESSAGES/main.po (msgstr)

# 4) Compile .mo — shipped in the pip wheel, .deb, and .rpm packages
msgfmt -o dev_project/i18n/ru_RU/LC_MESSAGES/main.mo \
  dev_project/i18n/ru_RU/LC_MESSAGES/main.po

# Shortcut: regenerate ru_RU from scripts/sync_i18n_catalog.py table + msgfmt
python3 scripts/sync_i18n_catalog.py

# Verify every _('...') in dev_project/ has a ru_RU table entry
python3 scripts/check_i18n_catalog.py
```

Compiled `dev_project/i18n/**/LC_MESSAGES/*.mo` files are tracked in git (see `.gitignore` exception) and shipped via `pyproject.toml` `package-data`. Locale behavior is covered by `tests/test_translations.py` and `tests/test_human_summaries.py`.

## Repository tests

Unit tests run on every push and pull request to `4.0-beta` and `main` via [GitHub Actions](https://github.com/aayartsev/odoo_dev_project/actions/workflows/ci.yml) (Python 3.10 and 3.12). The status badge at the top of this file reflects the latest run on `4.0-beta` after the workflow has been pushed at least once.

Local run (same command as CI):

```bash
cd /path/to/odoo_dev_project
pip install -e .
python3 -m unittest discover -s tests -p 'test_*.py'
```

Expect **634** tests passed and **7** skipped by default (opt-in Docker integration tests). Re-run manually in GitHub: **Actions → CI → Run workflow**.

### Lint (odpm repository)

Static analysis runs on **`dev_project/`**, **`tests/`**, and **`odpm.py`** only (not Odoo addons in a client project). CI job **`lint`** uses [ruff](https://docs.astral.sh/ruff/) in parallel with unit tests.

Local run (same scope as CI):

```bash
./scripts/lint.sh
# or: ruff check dev_project tests odpm.py
```

Optional pre-commit hook for contributors:

```bash
pip install pre-commit ruff   # or: uv tool install ruff
pre-commit install
pre-commit run --all-files
```

Rules live in `pyproject.toml` (`[tool.ruff]`). Legacy `.flake8` remains for reference; **ruff** is the primary linter.

### Docker CI

[`.github/workflows/ci-docker.yml`](.github/workflows/ci-docker.yml) runs in parallel with [unit CI](.github/workflows/ci.yml) on push/PR to `4.0-beta` and `main`.

#### CI matrix (4.2 policy)

| Job | Workflow | Trigger | Merge gate | Fixture / inputs |
|-----|----------|---------|------------|------------------|
| **lint** | `ci.yml` | every push/PR | **required** (recommended) | `ruff check` on `dev_project/`, `tests/`, `odpm.py` |
| **unit** | `ci.yml` | every push/PR | **required** (recommended) | `tests/` unittest discover; Python **3.10** and **3.12** |
| **release-packages** | `release-packages.yml` | push to `4.0-beta` / `4.0-rc1` / `main`, tag `v*`, or `workflow_dispatch` | optional | Build `.deb` + `.rpm`, lintian/rpmlint, install smoke; **Actions artifact** `release-packages` (+ per-job artifacts); **GitHub Release** assets on tag `v*` only |
| **compose-smoke** | `ci-docker.yml` | every push/PR | **required** (recommended) | [`tests/fixtures/minimal_odpm_project/`](tests/fixtures/minimal_odpm_project/) — stub platform/developing trees; `odpm --skip-start --no-git-update`, then `docker compose config`. Python **3.12** only. Base image cached between runs. |
| **golden-path** | `ci-docker.yml` | nightly (`03:00` UTC), `workflow_dispatch` (+ golden flag), or PR label **`run-docker`** | **opt-in** (not required on every PR) | Self-hosted runner (`self-hosted`, `Linux`, `X64`); variable `ODPM_GOLDEN_PATH_ENABLED=true` + secret `ODPM_GOLDEN_PATH_PROJECT` (`tests.integration.test_golden_path`). **Skipped** when variable unset — not a false pass. |

**PR label `run-docker`:** add the label on GitHub, then **re-run** the **CI Docker** workflow (adding a label alone does not start a new run).

**Local equivalents:**

```bash
# Compose smoke (same as CI compose-smoke job)
./scripts/run_compose_smoke_test.sh
# ODPM_COMPOSE_SMOKE_TIMEOUT=900 ./scripts/run_compose_smoke_test.sh

# Full golden-path (requires real project tree on disk)
ODPM_GOLDEN_PATH_PROJECT=/path/to/your-odpm-env ./scripts/run_golden_path_test.sh
```

#### CI secrets, variables, and branch protection

| Name | Kind | Required for | Notes |
|------|------|----------------|-------|
| `ODPM_GOLDEN_PATH_ENABLED` | variable | `golden-path` job only | Set to `true` when golden-path is configured on the self-hosted runner. Job `if:` cannot read secrets; this variable gates the job. |
| `ODPM_GOLDEN_PATH_PROJECT` | secret | `golden-path` job only | Absolute path to an initialized odpm project **on the self-hosted runner**. Set in GitHub Settings only — never commit the real path. Required when the variable is `true`; the job fails fast if the secret is missing or the directory is absent. |

**Self-hosted runner:** register a repo runner with labels `self-hosted`, `Linux`, `X64`. Compose smoke does **not** need the variable, secret, or self-hosted runner.

Recommended GitHub branch protection on `4.0-beta` / `main`: require status checks **CI** (**lint** + **unit**) and **CI Docker** / **compose-smoke** before merge. **golden-path** is a nightly or on-demand signal on the self-hosted runner; making it required on `main` only is a reasonable next step (4.3).

### Migration 4.0→4.1 imports

**As of 4.1.0, root-level shim modules under `dev_project/` are removed.** Custom scripts and extensions must use the canonical paths below. Imports of the old paths raise `ModuleNotFoundError`.

| Removed import (4.0 shim) | Use instead |
|---|---|
| `dev_project.prepare_registry` | `dev_project.prepare` |
| `dev_project.plan_compose_preview` | `dev_project.plan.compose_preview` |
| `dev_project.plan_runtime_preview` | `dev_project.plan.runtime_preview` |
| `dev_project.plan_compose_runtime` | `dev_project.plan.compose_runtime` |
| `dev_project.plan_diff` | `dev_project.plan.diff` |
| `dev_project.plan_format` | `dev_project.plan.format` |
| `dev_project.plan_cli` | `dev_project.plan.cli` |
| `dev_project.compose_service_builder` | `dev_project.compose.service_builder` |
| `dev_project.compose_runtime` | `dev_project.compose.runtime` |
| `dev_project.compose_command_render` | `dev_project.compose.command_render` |
| `dev_project.start_command` | `dev_project.compose.start_command` |
| `dev_project.host_context` | `dev_project.host.context` |
| `dev_project.host_runtime` | `dev_project.host.runtime` |
| `dev_project.host_user_env` | `dev_project.host.user_env` |
| `dev_project.host_cli` | `dev_project.host.cli` |
| `dev_project.host_cli.args` | `dev_project.host.cli.args` |
| `dev_project.host_cli.parse_args` | `dev_project.host.cli.parse_args` |
| `dev_project.host_cli.params` | `dev_project.host.cli.params` |
| `dev_project.inside_docker_app.cli_params` | `dev_project.host.cli.params` (host); checker flags: `dev_project.inside_docker_app.params` |
| `dev_project.inside_docker_app.parse_args` | `dev_project.host.cli.parse_args` (host only) |
| `dev_project.project_env.compose` | `dev_project.compose.generator.ComposeGenerator` or `from dev_project.compose import ComposeGenerator` |

Container-side checker flag names: `dev_project.inside_docker_app.params` (host CLI: `dev_project.host.cli.params`).


## How to start work

Create a folder where your new project environment will be located. At the end of the folder name, I add the odoo version number through a hyphen. For example, `my-odoo-project-17`. This is due to the fact that the difference between versions is significant, and I consider the same modules for different versions as different development projects. Each version of Odoo requires its own environment. Even though the code of the same project can be located in the same repository.To get the utility to start creating an environment, you need to navigate to the directory you created earlier, for example `my-odoo-project-17`, and then initialize it using the `--init` parameter command. As a parameter for the `--init` command, we can specify a link to a git repository (or a local directory). Also, by adding the `--branch` parameter, you can specify a specific branch to which you want to switch the repository of the project being developed. If the `--branch` parameter is not specified, the default branch will be selected:


Launch `VSCode` then threw menu File - Open Folder, open our folder `my-odoo-project-17`.

Now we cat enable Terminal threw menu Terminal - New Terminal. Then in it you can input commands that are written below. If someone, looking at a python script, wants to run it inside a virtual environment, then do not do this. In this case, it is used instead of system scripting languages and you will only complicate your life. The virtual environment for the project will be installed inside the container.

At the very first launch of the previously described command:
```bash
python3 /path/to/cloned/odoo_dev_project/odpm.py --init https://github.com/your-org/your-odoo-project.git --branch 17.0
```
If you do not wish to contact the `git` repository for any reason, you can easily create a local development environment by simply specifying a desired directory location.

```bash
python3 /path/to/cloned/odoo_dev_project/odpm.py --init file:///your/path/to/my-odoo-project-17/name_of_development_directory
```

The utility will try to prepare your computer:
1. The utility will ask questions about which parameters should be saved to a file `.env` (including the usage scenario: `developer` or `server`)
1. If you are deploying a project from scratch, the utility will ask you to specify the odoo version and make initial settings based on this information
1. The cloning process of the main odoo repository will be started. This takes a very significant time of 40 minutes or more, so be patient
1. The repository of the developed project will be cloned, or the directory of the local file system will be connected if a path to the file system was specified.
1. A `Dockerfile` will be automatically generated for the specified `python` and `debian` version.
1. A `.dockerignore` in the project root is generated from the `.odpm/dockerignore` template (Docker build context).
1. After this, the automatic build of the `Docker image` will start if it has not been built before.
1. The `docker-compose.yml` file will be automatically generated
1. Configuration files will be generated for VS Code for the debugger to work correctly (`.odpm/runtime/debug-profile.json` plus `.vscode/launch.json` in the `developer` scenario)
1. A `secrets.example.json` template is placed under `.odpm/`; optional module secrets live in gitignored `.odpm/secrets.json` and mount to `/run/odpm/secrets.json` in `developer`/`server` (see [docs/operations/secrets.md](docs/operations/secrets.md))
1. `docker-compose up` will start automatically
1. All python dependencies will be installed in the virtual environment
1. Odoo will start with all specified addons for selected version

You can stop this running process by using the keyboard shortcut `Ctrl+C`.

After that, you can run odoo in developer mode:
```bash
python3 /path/to/cloned/odoo_dev_project/odpm.py -d test_db -i -u
```
This command will launch odoo inside the `Docker container` and create a new database named `test_db` and install the module from the specified project there

After that, you can open the address `http://127.0.0.1:8069` in the browser and you will see the login window.

2 configuration files are required for the system to work:
- `odpm.json` -  it also can be located in the repository with the developing project, contains the necessary information on how to start this project. If the file is not found, it will be created from the default values.
- `user_settings.json` - contains the settings and preferences of a specific developer. If the file is not found, it will be created from the default values.

## Short summary

This app build environment for your project. The project itself is a directory that is specified in a parameter `developing_project` of `user_settings.json` file or as key of `--init` param.

### `.dockerignore` template

Edit Docker build exclusions in `.odpm/dockerignore` (copied from odpm when the project is initialized). On every odpm run, the root `.dockerignore` is regenerated from that template — do not edit the root file by hand. To reset the template to odpm defaults, delete `.odpm/dockerignore` and run odpm again.

## Parameters in .env file:
The system will try to create a `.odpm` directory in the user's home directory of your operating system. Inside it the system will place the `.env` file. If you are launching the application for the first time, it will ask a question for each item described below in this file and offer default values. If you don't know what to answer, just press `Enter`. If you place the `.env` file in the project directory, the program will consider it a priority and try to take values from the file inside the project.
- `BACKUP_DIR` - the directory where the archives are located. It is used to specify the name of the database for recovery using command-line parameters and then the system will search for an archive with the specified name in this directory, or when saving the database to the archive, it will appear in this directory, can be used for all projects
- `ODOO_PROJECTS_DIR` - create a directory where clones of all used repositories will be created. You just need specify the path to this directory, then the system itself will create this directory and clone all the repositories into it and arrange them so that there are no conflicts
- `ODOO_PORT` - the port on which odoo will be launched by default at the address 127.0.0.1
- `POSTGRES_PORT` - the port on which the PostgreSQL DBMS will be launched by default at the address 127.0.0.1
- `DEBUGGER_PORT` - the port on which the debugger will run by default at the address 127.0.0.1
- `GEVENT_PORT` - the port on which the Websocket Gevent System will listen by default at the address 127.0.0.1
- `ODPM_SCENARIO` - usage scenario for odpm: `developer` (default), `server`, or `ci`. See [Usage scenarios](#usage-scenarios-odpm_scenario) below.

Example:
```conf
BACKUP_DIR=/home/user/odoo_backups
ODOO_PROJECTS_DIR=/home/user/odoo_projects
PATH_TO_SSH_KEY=
ODOO_PORT=8069
POSTGRES_PORT=5432
DEBUGGER_PORT=5678
GEVENT_PORT=8072
ODPM_SCENARIO=developer
```

The first-run wizard does **not** ask for an SSH key. Git uses your normal OpenSSH setup (`~/.ssh/config`, ssh-agent, default keys). Leave `PATH_TO_SSH_KEY` empty unless you need an override (see below).

### Advanced: `PATH_TO_SSH_KEY` (optional)

Set this only when git cannot use your default SSH stack (for example ssh-agent is unavailable in CI). odpm then runs git with `core.sshCommand=ssh -i <path>`. One key applies to all git remotes. Example:

```conf
PATH_TO_SSH_KEY=/home/user/.ssh/id_ed25519
```

## Non-interactive mode (CI, scripts)

When stdin is not attached to a terminal (no TTY), odpm **does not prompt** via `input()`. In the **server** scenario, if platform sources (`odoo-bin`) are missing locally, odpm would normally ask to download a nightly zip; without a TTY it **fails fast** instead — pre-install platform sources, run from an interactive terminal, or use `ODPM_SCENARIO=developer` for git-based clone during prepare.

**`.env` file** — must already exist in the project directory or at `~/.odpm/.env`. For the first run you can instead set at least one of the environment variables below; odpm will create `~/.odpm/.env` and fill the rest from defaults:

- `BACKUP_DIR`, `ODOO_PROJECTS_DIR`
- `ODOO_PORT`, `POSTGRES_PORT`, `DEBUGGER_PORT`, `GEVENT_PORT`
- `ODPM_SCENARIO`
- `PATH_TO_SSH_KEY` (optional advanced override)

**Creating `odpm.json`** — on `--init` without an existing `odpm.json` in the developing project, pass `--odoo-version` or ensure `odoo_version` is present in the cloned repo's `odpm.json`.

Example for CI:

```bash
export ODPM_SCENARIO=ci
export ODOO_PROJECTS_DIR=/data/odoo_projects
export BACKUP_DIR=/data/backups
odpm --init https://github.com/acme/demo.git --skip-start
```

## Usage scenarios (`ODPM_SCENARIO`)

On the first run, odpm asks you to choose a scenario by number (`1` — developer, `2` — server, `3` — ci). The value is stored in `.env` as `ODPM_SCENARIO`. You can change it later and regenerate `docker-compose.yml` by running odpm again.

The scenario does **not** replace `odpm.json` or `user_settings.json`. It changes Docker ports, how Odoo starts (with or without `debugpy`), and how the Python venv is managed (`fresh` vs `baked`; see comparison table).

### `developer` (default)

Use on a **local workstation** when you develop modules, debug code in VS Code, and need Odoo developer features.

| Area | Behavior |
|------|----------|
| **debugpy** | Enabled **inside the container** by `run_odoo` when `ODPM_SCENARIO=developer` (not in the compose `command` list). Listens on `0.0.0.0:5678`; the debugger port is published on the host. |
| **PostgreSQL / debugger on host** | Published as `HOST_PORT:CONTAINER_PORT` (not restricted to loopback on the host). |
| **Odoo / Gevent** | Published on the host on `ODOO_PORT` and `GEVENT_PORT`. |
| **`dev_mode` in `user_settings.json`** | Passed to Odoo as `--dev` in compose (not a separate odpm CLI flag). Values: `reload`, `qweb`, `werkzeug`, `xml`, `access`, `all`, or comma-separated combinations. When `reload` or `all` is set, `inotify` is added to the venv automatically. Regenerate compose with `odpm --skip-start` after changing `dev_mode`. |

Typical workflow: `ODPM_SCENARIO=developer`, attach the debugger from VS Code, open `http://127.0.0.1:8069`.

### `server`

Use on a **machine that runs Odoo as a service** (staging/production, VPS). Focus: less exposure of infrastructure ports and no debugger in the Odoo process.

| Area | Behavior |
|------|----------|
| **debugpy** | **Not** installed and **not** added to the Odoo start command. To debug, switch to `ODPM_SCENARIO=developer` and recreate the environment. |
| **PostgreSQL on host** | Bound to `127.0.0.1:POSTGRES_PORT` only (not reachable from other machines via the published port). |
| **Debugger port in compose** | **Not published** (Odoo does not use debugpy). |
| **Odoo / Gevent on host** | Still published as `ODOO_PORT` / `GEVENT_PORT` on all host interfaces — put a reverse proxy (nginx, traefik) and firewall in front for public access. |
| **`dev_mode`** | **Ignored** when scenario is `server` (logged warning). Leave empty in `user_settings.json` on production. |

### `ci` (CI / DevOps)

For **building and running a baked image** on a CI runner: sources and venv live inside the Docker image; no bind-mount of Odoo directories.

| Area | Behavior |
|------|----------|
| **Image** | Project-specific CI image (`odpm --build-image`, only when `ODPM_SCENARIO=ci`) |
| **Odoo volumes** | No bind-mount of sources |
| **debugpy / debugger port** | No (debugpy is not installed in `ci`) |
| **Gevent 8072** | Yes (same as dev/server) |
| **Entrypoint** | Compose `command` is exec form: `python3 -m dev_project.inside_docker_app.run_odoo`; project config is mounted from `.odpm/runtime/config.json` (`venv_mode=baked`) |
| **VS Code** | Not configured |
| **`dev_mode`** | **Ignored** (same as `server`) |

Typical on a runner: `ODPM_SCENARIO=ci`, `odpm --build-image`, then `docker compose up`.

**Manual verification** (full project with real Odoo sources):

```bash
export ODPM_SCENARIO=ci
./scripts/verify_ci_scenario.sh
```

The script runs `python3 odpm.py --build-image`, `docker compose up -d`, and waits for HTTP 200 on `/web`.

**Opt-in docker integration tests** (require Docker on the host; skipped by default in `unittest discover`):

```bash
# Compose smoke: minimal fixture + odpm --skip-start + docker compose config
./scripts/run_compose_smoke_test.sh

# CI image bake only (minimal context, no compose)
ODPM_RUN_DOCKER_INTEGRATION=1 python3 -m unittest tests.integration.test_ci_image_build -v

# Golden path: compose up + HTTP 200 on /web (full initialized project)
export ODPM_GOLDEN_PATH_PROJECT=/path/to/your/odpm/project
# Run from the odpm repository root (tests/ lives there), or use the helper script:
./scripts/run_golden_path_test.sh
# Equivalent:
# cd /path/to/odoo_dev_project && ODPM_RUN_DOCKER_INTEGRATION=1 python3 -m unittest tests.integration.test_golden_path -v
```

Optional: `ODPM_GOLDEN_PATH_TIMEOUT=600` (seconds, default 300). Stop the project's default compose stack first (`docker compose down` in the project directory): the golden-path test reuses the same Postgres data directory and uses ephemeral host ports (Postgres is not published; Odoo HTTP is mapped to a free port).

Requires Docker on the host. Skipped by default in `unittest discover` (fast CI).

### Comparison

| | `developer` | `server` | `ci` |
|---|---------------|----------|------|
| Remote debug (debugpy) | Yes | No | No |
| Postgres on host | All interfaces | `127.0.0.1` only | `127.0.0.1` only |
| Debugger port in compose | Yes | No | No |
| Odoo bind-mount | Yes | Yes | No |
| Python venv (`venv_mode`) | `fresh` — recreated when lock changes | `fresh` — same as developer | `baked` — pre-built in image, no recreate |
| `--build-image` | Error | Error | Yes |
| Odoo `--dev` (`dev_mode`) | Yes | No (ignored) | No (ignored) |
| Recommended environment | Local PC / laptop | Server / VPS | CI runner |

### Switching scenario

1. Edit `ODPM_SCENARIO` in `~/.odpm/.env` or in the project `.env`.
2. Run odpm from the project directory (e.g. `python3 .../odpm.py --skip-start`) so `docker-compose.yml` is regenerated.
3. Restart containers: `docker compose up -d` (or run odpm without `--skip-start`).

Generated `docker-compose.yml` uses exec-form `command:` (YAML list), `working_dir`, and a read-only mount of `.odpm/runtime/config.json` into the container. That runtime file is auto-generated (JSON with `schema_version: 1`, typed as `ContainerConfig`) and gitignored — do not edit compose manually; regenerate with `odpm --skip-start` after upgrading odpm or changing scenario/CLI flags. Compose passes config via the mount and `ODPM_CONFIG_PATH`. The container entrypoint is `python3 -m dev_project.inside_docker_app.run_odoo`.

### Recommendations for `server`

- Ensure Odoo platform sources are present under `odoo_src_dir` before running odpm in CI or scripts (non-interactive). Interactive first-time setup may download a nightly zip when prompted; headless runs require a pre-populated tree or `developer` scenario.
- `dev_mode` in `user_settings.json` is ignored on `server`; do not switch to `developer` on a publicly reachable instance just to enable `--dev`.
- Set strong values for `db_manager_password`, `db_default_admin_*`, and PostgreSQL credentials; do not rely on image defaults.
- Prefer HTTPS via a reverse proxy; set Odoo `proxy_mode` and `dbfilter` in `odoo.conf` when exposing the instance.
- Restrict inbound traffic with a host firewall (allow only SSH and HTTPS; block direct access to `8069`/`8072` from the internet if the proxy is on the same host).
- For database administration from the host only, `127.0.0.1` binding of Postgres is sufficient; do not map `5432` to `0.0.0.0` manually in compose.

## Parameters in user_settings.json:

- `init_modules` - `type: String`. Parameter that specifies modules separated by commas, without spaces, which will be initiated (installed) when (re)starting the system.
- `update_modules` - `type: String` A parameter that specifies modules separated by commas, without spaces, which will be updated when (re)starting the system
- `db_creation_data` - `type: Object`. The parameters that determine the creation of a new database.
    - `db_lang` - `type: String`. Specify the default system language when creating a new database, for example: `"en_US"` or `"ru_RU"`
    - `db_country_code` - `type: String` or `false`. Specify the default country code for creating a new database, for example:`"by"`
    - `create_demo` - `type: Boolean`. Indicates whether it is necessary to create demo data in the system when creating a new database.
    - `db_default_admin_login` - `type: String`. Login for the administrator account
    - `db_default_admin_password` - `type: String`. The password for the administrator account
- `update_git_repos` - `type: Boolean`. Indicates whether the dependency repositories and odoo itself will be updated when the system is restarted
- `clean_git_repos` - `type: Boolean`. Indicates whether changes to odoo itself and dependency projects will be reset on restart
- `check_system` - `type: Boolean`. Default `true`. When `true`, enables beginner checks gated by `SystemCheckPolicy` (`dev_project/system_check_policy.py`): `beginner_git` (`git --version` at pipeline setup) and prepare step `docker.engine.check` (Docker group membership, `docker info`, base image). Does **not** control port release — `developer_port_release` runs prepare step `docker.ports.release` in the **developer** scenario only, even when `check_system` is `false`. Does **not** gate `compose.validate` (`compose_validate` is always enabled). `file_system_on_init` always ensures backup/project directories on checker init and validates the platform git tree in the **developer** scenario (clone/update runs later in prepare step `git.materialize`, not during init). Free disk space is checked only when odpm clones Odoo sources, not via this flag.
- `developing_project` - `type: String`.A link to the project you are developing. Example: `"git@github.com:your-org/your-odoo-project.git"`
- `pre_commit_map_files` - `type: String`. A list of files for the `pre-commit` system that are taken out of the project and pushed there through the docker file mapping. It is necessary to work on non-Linux systems
- `dev_mode` - `type: String` or `false`. Comma-separated [Odoo `--dev` flags](https://www.odoo.com/documentation/16.0/developer/reference/cli.html?highlight=dev#cmdoption-odoo-bin-dev) (`reload`, `qweb`, `werkzeug`, `xml`, `access`, `all`). **Only applied when `ODPM_SCENARIO=developer`**; on `server`/`ci` the value is ignored with a warning. When `reload` or `all` is set, odpm adds `inotify` to Python requirements for code autoreload. Regenerate compose after changes (`odpm --skip-start`).
- `db_manager_password` - `type: String`. password for the database manager
- `sql_queries` - `type: List`. Contains a list of strings, each of which is an SQL script that will be executed when using the command line parameter `--sql-execute`
- `use_oca_dependencies` - experimental dependency discovery (single odpm run, default `false`): reads `oca_dependencies.txt` from the developing project and each checked-out git dependency, **and** nested `odpm.json` at dependency repo roots (`dependencies`, `requirements_txt`). Transitive git URLs are included in the resolved graph and in `.odpm/deps.lock.json` on `--update-lock`. Nested `odoo_version` / `python_version` are checked against the host project (warning in developer scenario, error in CI). Does not override host `odoo_git_link` or platform settings.
- `create_module_links` - optional experimental feature that adds soft links for all modules involved in the project to the platform `odoo/addons` tree under `odoo_src_dir`. Project-root symlinks (`odoo`, developing project, `dependencies/*`) are always refreshed on each `odpm` run. Debugger `path_mappings` (in `.odpm/runtime/debug-profile.json` and `.vscode/launch.json`) include **both real on-disk directories and project symlink paths** — breakpoints work when you open files via `project/...` in the odpm tree or via `~/odoo_projects/...`. Default `false`.

## Parameters in odpm.json:
- `python_version` - `type: String`. The python version is indicated in text form by its number, for example `"3.10"` or `"3.7"`,
- `distro_name` - `type: String`. The name of the distribution on which the image for running Odoo will be created. Currently, only `"debian"` is supported.
- `distro_version` - `type: String`. The version of the distribution specified in the distro_name key, indicated as a text version, for example, `"11"` or `"12"`
- `postgres_version` - `type: String`. PostgreSQL version for Docker Compose (e.g. `"15"`).
- `odoo_version` - `type: String`. The version of the odoo system. Examples: `"16.0"`, `"15.0"`, `"11.0"`
- `dependencies` - `type: List`. A list of links to the project repositories on which your project depends
- `requirements_txt` - `type: List`. A list of python modules, each element can be formatted in the same way as a line in a file requirements.txt
- `odoo_git_link` - `type: String`. Platform repository URL; optional branch/commit after a space (same format as CLI `--odoo-git-link`).
- `platform_name` - `type: String`. Python package name for a custom fork (default `"odoo"`).
- `odoo_build_date` - `type: String`. Nightly build date (`YYYYMMDD`) or `"latest"`. Checkout matching commit on the platform branch. Overridden by CLI `--odoo-build-date`.
- `odpm_version` - `type: String`. odpm format version of the project file.

### Supported Linux Distributions and Versions with Python Versions

Currently, for Odoo versions 11 to 16 inclusive, Python 3.7 on Debian 11 (Bullseye) has been tested and works stably.
Also tested and works stably for Odoo versions 16 to 17 with Python 3.10 on Debian 11 (Bullseye) and Debian 12 (Bullseye).
Experimental support for Ubuntu distributions has begun, but it is still in its early stages, and all experiments are at your own discretion.
Supported distributions and versions:

- Stable:
    - Debian 11 (Bullseye)
        - Python 3.7, 3.10
    - Debian 12 (Bullseye)
        - Python 3.10
- Experimental:
    - Ubuntu 22.04 (Jammy)
        - Python 3.10
    - Ubuntu 20.04 (Focal)
        - Python 3.8

## Command line parameters

Run `python3 /path/to/odpm.py --help` for the full list. Parameters below are grouped by purpose.

### Project initialization

| Parameter | Description |
|-----------|-------------|
| `--init LINK` | Initialize the current directory as an odpm project. `LINK` is a git URL, `git@…` SSH URL, or `file:///path/to/local/project`. |
| `--branch NAME` | With `--init`: branch of the **developing** project repository to clone. |
| `--odoo-version VER` | With `--init`: Odoo version (e.g. `17.0`). Used when creating `odpm.json`. |
| `--odoo-git-link LINK` | With `--init`: platform Odoo repository instead of official `odoo/odoo`. May include branch (and optional commit), e.g. `'git@host:org/odoo-17.git 17.0'`. Saved to `odpm.json`. |
| `--platform-name NAME` | With `--init` / custom git link: Python package name of the fork (default `odoo`). Affects paths and `odoo-bin` command inside the container. |
| `--python-version VER` | With `--init`: Python version for the Docker image (e.g. `3.10`). |
| `--distro-name NAME` | With `--init`: Linux distribution name (currently `debian`). |
| `--distro-version VER` | With `--init`: distribution version (e.g. `12`). |
| `--postgres-version VER` | With `--init`: PostgreSQL version for compose (e.g. `15`). |
| `--requirements-txt PKGS` | Comma-separated pip packages with versions, e.g. `requests==2.31.0,cryptography==42.0.8`. Written to `odpm.json`. |

Example:

```bash
python3 odpm.py --init git@github.com/org/my_addons.git --branch 17.0 \
  --odoo-version 17.0 --odoo-git-link 'git@github.com/org/odoo-17.git 17.0' \
  --platform-name odoo --python-version 3.10 --distro-version 12
```

### Environment and image

| Parameter | Description |
|-----------|-------------|
| `--skip-start` | Regenerate `Dockerfile`, `.dockerignore`, `docker-compose.yml` (and related files) and **do not** start containers. Useful after changing `.env` or scenario. With a committed `.odpm/deps.lock.json`, also checks out pinned git SHAs before compose. |
| `--update-lock` | Resolve platform, developing (remote git), and **full resolved** dependency graph (OCA + nested `odpm.json`); write `.odpm/deps.lock.json`; exit without starting containers (combine with `--skip-start` in CI). |
| `--no-git-update` | Skip git clone/fetch/checkout. Lock file is **not** read or updated. Requires existing local repos. |
| `--plan` | **Deprecated.** Same as `odpm plan` (see [Plan (dry-run)](#plan-dry-run) below). |
| `--version` | Print odpm version and exit. |

### Plan (dry-run)

Preview which prepare and runtime steps would run on a normal invocation **without** cloning or updating git repositories, writing generated project files (runtime config, root `docker-compose.yml`), or running `docker compose up`.

```bash
odpm plan --skip-start
odpm plan --plan-format json | jq .
odpm plan --plan-show-diff --skip-start
```

`--plan` is a deprecated alias; all project flags (`--skip-start`, `--no-git-update`, and so on) work the same after `odpm plan`.

| Parameter | Description |
|-----------|-------------|
| `--plan-format {table,json}` | Output format. Default `table` (logged). `json` is written to **stdout** for scripts (`jq`, CI). |
| `--plan-strict` | Exit with code `1` when any **required** step would `run` or `update`; `0` when only noop, skip, or optional steps would change. |
| `--plan-show-diff` | After the step table, print unified diffs for files that would change: `.odpm/runtime/config.json`, root `docker-compose.yml`, root `.dockerignore`. |
| `--plan-no-docker` | Skip `docker compose ps` / `inspect` probe; `compose.up` will not predict `--force-recreate` (a warning is shown). |

Each step shows an outcome (`RUN`, `UPDATE`, `NOOP`, `SKIP`), whether it is required, an id (for example `git.materialize`, `compose.service`), and a short reason. When the stack is running and healthy, `compose.up` is planned without `--force-recreate`; otherwise recreate is predicted (unless `--plan-no-docker` or `--skip-start`).

**Limits:** Configuration is still loaded from the project directory. Plan mode does not upgrade templates under `.odpm/` (a normal `odpm` run still syncs them). Unless `--plan-no-docker` is set, odpm may probe the local compose stack to predict `compose.up`. Combine with `--skip-start` to omit `compose.up` from the plan.

### Odoo run: database and modules

| Parameter | Description |
|-----------|-------------|
| `-d DB_NAME` | Database name. Created automatically from `db_creation_data` in `user_settings.json` if missing. |
| `-i` | Install modules listed in `init_modules` (`user_settings.json`). |
| `-u` | Update modules listed in `update_modules` (`user_settings.json`). |
| `-t`, `--test` | Run tests for modules from `init_modules` / `update_modules`. Requires `-d` and usually `-i` or `-u`. On a fresh DB, tests for all installed modules may run (slow). |
| `--screencasts` | With `-t` / `--test`: save screencast videos for tour failures under `data/odoo/tmp/odoo_tests` in the project. |
| `--odoo-bin ARGS…` | Pass arguments to `odoo-bin` (everything after `--odoo-bin`). Example: `--odoo-bin --stop-after-init`. |

Typical development run:

```bash
python3 odpm.py -d test_db -i -u
```

Init and stop (CI / first setup):

```bash
python3 odpm.py -d test_db -i --odoo-bin --stop-after-init
```

### Platform git: nightly build date

| Parameter | Description |
|-----------|-------------|
| `--odoo-build-date DATE` | Odoo nightly date: `YYYYMMDD` or `YYYY-MM-DD`. Resolves the last commit on the platform branch before that day and checks it out. Overrides `odoo_build_date` in `odpm.json`. Ignored if a commit hash is set in `odoo_git_link`. |

Example:

```bash
python3 odpm.py --skip-start --odoo-build-date 20250529
```

### Git dependency lock (`.odpm/deps.lock.json`)

Committed lock file with pinned git SHAs (and file-platform fingerprints) for reproducible CI and team sync.

| Command | Behavior |
|---------|----------|
| `python3 odpm.py --update-lock --skip-start` | Refresh lock from branch tips / current trees (full dependency graph including OCA and nested `odpm.json`); exit without compose up |
| `python3 odpm.py --skip-start` | Normal prepare + checkout **by lock** if file exists |
| `python3 odpm.py --no-git-update --skip-start` | Offline regenerate Docker files; lock ignored |

After changing `dependencies`, `oca_dependencies.txt`, or nested dependency `odpm.json`, run `--update-lock` and commit `.odpm/deps.lock.json`.

Lock schema (v1): `platform` (required), optional `developing` (remote git only), `dependencies` (full resolved list: seeds, OCA transitive, nested `odpm.json` transitive). Each entry has `url`, `commit`, optional `branch`, optional `kind` (`git` default, `file` for `file://` platform trees).

For `file://` platform trees, `commit` is a content fingerprint (not a git SHA). It is stable when `odoo/release.py` and `odoo-bin` are present; otherwise it may differ across machines or after directory metadata changes — prefer git remotes for CI and team sync when reproducibility matters.

Precedence: `--no-git-update` > `--update-lock` > existing lock (pins SHAs, skips `odoo_build_date` for locked platform) > legacy branch tip / build date.

**Developer scenario** (`ODPM_SCENARIO=developer`, default): lock applies to **platform** and **dependencies** only; the **developing** project git tree is left under developer control. The `developing` entry is still written on `--update-lock` (for CI/server) and enforced in `ci` / `server` scenarios.

### Database backup and maintenance

| Parameter | Description |
|-----------|-------------|
| `--get-dbs-list` | List databases (inside the running environment). |
| `--db-backup [ARCHIVE]` | Backup the database from `-d` into `BACKUP_DIR` (`.env`). Optional archive name; otherwise name + timestamp. |
| `--db-restore ARCHIVE` | Restore archive from `BACKUP_DIR` into the database named in `-d`. |
| `--db-drop` | Drop the database named in `-d`. With `-d`, `-i`, `-u` and the same name: drop, recreate, install modules. |

### Translations and admin

| Parameter | Description |
|-----------|-------------|
| `--translate LANG` | Update translations (e.g. `ru_RU`) for DB `-d` and modules from `init_modules` / `update_modules`. Use with `-d`, `-i`, or `-u`. |
| `--export-po-files LANG` | Export `pot` / `po` for `LANG` and modules from `update_modules`. Requires `-d`. |
| `--set-admin-pass` | Set admin (uid=2) login/password from `db_default_admin_login` / `db_default_admin_password` in `user_settings.json`. Requires `-d`. |

### Development tools

| Parameter | Description |
|-----------|-------------|
| `--start-precommit` | Run `pre-commit` in the developing project inside the container. |
| `--sql-execute` | Run SQL from `sql_queries` in `user_settings.json`. Requires `-d`. |

### Scaffold subcommand

Creates a module in the developing project (run **without** other odpm flags):

```bash
python3 odpm.py scaffold my_module_name
python3 odpm.py scaffold my_module_name -t /path/to/template_dir
```

| Parameter | Description |
|-----------|-------------|
| `scaffold MODULE` | Subcommand: generate a module from templates ([jinja2](https://jinja.palletsprojects.com/en/stable/)). |
| `-t`, `--scaffold_template_name DIR` | Custom template directory. |
