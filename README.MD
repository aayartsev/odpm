[![ru](https://img.shields.io/badge/lang-ru-green.svg)](https://github.com/aayartsev/odoo_dev_project/blob/3.0/README-RU.MD)

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

If you are new, i recommend using this project in conjunction with the training demo [`https://github.com/aayartsev/odoo_demo_project`](https://github.com/aayartsev/odoo_demo_project).

## Prepare
You need to download and install the following programs:
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) for Windows and MacOS users
- [git](https://git-scm.com/)
- [python3](https://www.python.org/)
- [Visual Studio Code](https://code.visualstudio.com/)


## How to start work

Create a folder where your new project environment will be located. At the end of the folder name, I add the odoo version number through a hyphen. For example, `odoo_demo_project-17`. This is due to the fact that the difference between versions is significant, and I consider the same modules for different versions as different development projects. Each version of Odoo requires its own environment. Even though the code of the same project can be located in the same repository.To get the utility to start creating an environment, you need to navigate to the directory you created earlier, for example `odoo_demo_project-17`, and then initialize it using the `--init` parameter command. As a parameter for the `--init` command, we can specify a link to a git repository (or a local directory). Also, by adding the `--branch` parameter, you can specify a specific branch to which you want to switch the repository of the project being developed. If the `--branch` parameter is not specified, the default branch will be selected:


Launch `VSCode` then threw menu File - Open Folder, open our folder `odoo_demo_project-17`.

Now we cat enable Terminal threw menu Terminal - New Terminal. Then in it you can input commands that are written below. If someone, looking at a python script, wants to run it inside a virtual environment, then do not do this. In this case, it is used instead of system scripting languages and you will only complicate your life. The virtual environment for the project will be installed inside the container.

At the very first launch of the previously described command:
```bash
python3 /path/to/cloned/odoo_dev_project/odpm.py --init https://github.com/aayartsev/odoo_demo_project.git --branch 17.0-test_odpm_json
```
If you do not wish to contact the `git` repository for any reason, you can easily create a local development environment by simply specifying a desired directory location.

```bash
python3 /path/to/cloned/odoo_dev_project/odpm.py --init file:///your/path/to/odoo_demo_project-17/name_of_development_directory
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
1. Configuration files will be generated for VS Code for the debugger to work correctly
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
- `PATH_TO_SSH_KEY` - if, for some reason, you are unable to add your repository key to the ssh agent, then you can specify the path to it here. At the moment, one key will be used for all repositories
- `ODOO_PORT` - the port on which odoo will be launched by default at the address 127.0.0.1
- `POSTGRES_PORT` - the port on which the PostgreSQL DBMS will be launched by default at the address 127.0.0.1
- `DEBUGGER_PORT` - the port on which the debugger will run by default at the address 127.0.0.1
- `GEVENT_PORT` - the port on which the Websocket Gevent System will listen by default at the address 127.0.0.1
- `ODPM_SCENARIO` - usage scenario for odpm: `developer` (default), `server`, or `ci`. See [Usage scenarios](#usage-scenarios-odpm_scenario) below.

Example:
```conf
BACKUP_DIR=/home/user/odoo_backups
ODOO_PROJECTS_DIR=/home/user/odoo_projects
PATH_TO_SSH_KEY=/home/user/.ssh/my_ssh_key
ODOO_PORT=8069
POSTGRES_PORT=5432
DEBUGGER_PORT=5678
GEVENT_PORT=8072
ODPM_SCENARIO=developer
```

## Non-interactive mode (CI, scripts)

When stdin is not attached to a terminal (no TTY), odpm **does not prompt** via `input()`.

**`.env` file** — must already exist in the project directory or at `~/.odpm/.env`. For the first run you can instead set at least one of the environment variables below; odpm will create `~/.odpm/.env` and fill the rest from defaults:

- `BACKUP_DIR`, `ODOO_PROJECTS_DIR`, `PATH_TO_SSH_KEY`
- `ODOO_PORT`, `POSTGRES_PORT`, `DEBUGGER_PORT`, `GEVENT_PORT`
- `ODPM_SCENARIO`

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
| **debugpy** | Odoo starts with `debugpy` listening inside the container (`0.0.0.0:5678`). The debugger port is published on the host (all interfaces, same as other published ports). |
| **PostgreSQL / debugger on host** | Published as `HOST_PORT:CONTAINER_PORT` (not restricted to loopback on the host). |
| **Odoo / Gevent** | Published on the host on `ODOO_PORT` and `GEVENT_PORT`. |
| **`dev_mode` in `user_settings.json`** | Applied when passed on the command line (e.g. assets reload). Suitable for daily development. |

Typical workflow: `ODPM_SCENARIO=developer`, attach the debugger from VS Code, open `http://127.0.0.1:8069`.

### `server`

Use on a **machine that runs Odoo as a service** (staging/production, VPS). Focus: less exposure of infrastructure ports and no debugger in the Odoo process.

| Area | Behavior |
|------|----------|
| **debugpy** | **Not** installed and **not** added to the Odoo start command. To debug, switch to `ODPM_SCENARIO=developer` and recreate the environment. |
| **PostgreSQL on host** | Bound to `127.0.0.1:POSTGRES_PORT` only (not reachable from other machines via the published port). |
| **Debugger port in compose** | **Not published** (Odoo does not use debugpy). |
| **Odoo / Gevent on host** | Still published as `ODOO_PORT` / `GEVENT_PORT` on all host interfaces — put a reverse proxy (nginx, traefik) and firewall in front for public access. |
| **`dev_mode`** | Not disabled automatically; for production, leave `dev_mode` empty in `user_settings.json` and do not use developer-only flags. |

### `ci` (CI / DevOps)

For **building and running a baked image** on a CI runner: sources and venv live inside the Docker image; no bind-mount of Odoo directories.

| Area | Behavior |
|------|----------|
| **Image** | Project-specific CI image (`odpm --build-image`, only when `ODPM_SCENARIO=ci`) |
| **Odoo volumes** | No bind-mount of sources |
| **debugpy / debugger port** | No (debugpy is not installed in `ci`) |
| **Gevent 8072** | Yes (same as dev/server) |
| **Entrypoint** | `python3 -m dev_project.inside_docker_app.main` (full `dev_project/` package in the image, `venv_mode=baked`) |
| **VS Code** | Not configured |

Typical on a runner: `ODPM_SCENARIO=ci`, `odpm --build-image`, then `docker compose up`.

### Comparison

| | `developer` | `server` | `ci` |
|---|---------------|----------|------|
| Remote debug (debugpy) | Yes | No | No |
| Postgres on host | All interfaces | `127.0.0.1` only | `127.0.0.1` only |
| Debugger port in compose | Yes | No | No |
| Odoo bind-mount | Yes | Yes | No |
| Python venv (`venv_mode`) | `fresh` — recreated when lock changes | `fresh` — same as developer | `baked` — pre-built in image, no recreate |
| `--build-image` | Error | Error | Yes |
| Recommended environment | Local PC / laptop | Server / VPS | CI runner |

### Switching scenario

1. Edit `ODPM_SCENARIO` in `~/.odpm/.env` or in the project `.env`.
2. Run odpm from the project directory (e.g. `python3 .../odpm.py --skip-start`) so `docker-compose.yml` is regenerated.
3. Restart containers: `docker compose up -d` (or run odpm without `--skip-start`).

### Recommendations for `server`

- Do not use `dev_mode` on a publicly reachable instance.
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
- `check_system` - `type: Boolean`. Indicates whether the system check will be started at startup. Useful for beginners. Checks if `git`, `docker`, and `docker-compose` are installed.
- `developing_project` - `type: String`.A link to the project you are developing. Example: `"git@github.com:aayartsev/odoo_demo_project.git "`
- `pre_commit_map_files` - `type: String`. A list of files for the `pre-commit` system that are taken out of the project and pushed there through the docker file mapping. It is necessary to work on non-Linux systems
- `dev_mode` - `type: String`. You can specify comma-separated [parameters for developers](https://www.oovoo.com/documentation/16.0/developer/reference/cli.html?highlight=dev#cmdoption-odoo-bin-dev). See the official documentation for your version of odoo
- `db_manager_password` - `type: String`. password for the database manager
- `sql_queries` - `type: List`. Contains a list of strings, each of which is an SQL script that will be executed when using the command line parameter `--sql-execute`
- `use_oca_dependencies` - experimental: automatically resolves dependencies from `"oca_dependencies.txt"` (including transitive OCA repos from your developing project and from each dependency) in a **single odpm run**—no second run is required. The default value is `false`
- `create_module_links` - an experimental feature that adds soft links for all modules involved in the project to the `odoo/odoo/addons` directory. This allows the language server to automatically resolve import paths. The default value is `false`.

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
| `--skip-start` | Regenerate `Dockerfile`, `.dockerignore`, `docker-compose.yml` (and related files) and **do not** start containers. Useful after changing `.env` or scenario. |
| `--version` | Print odpm version and exit. |
| `--config-base64-data STRING` | Decode a base64 JSON config string (advanced / automation). |

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
