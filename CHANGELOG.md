# Changelog

All notable changes to **odpm** (Odoo Developer Project Manager) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [4.0.0] - 2026-06-06

Version 4.0 is a major architectural release. The user-facing goal is unchanged: prepare a reproducible Odoo development environment from `odpm.json`. The implementation was rebuilt around a host pipeline, typed container configuration, three usage scenarios, reproducible git dependency locking, and an installable Python package.

### Breaking Changes

- **Removed legacy host modules and import paths.** Deleted: `host_config.py`, `host_project_env.py`, `handle_odoo_project_git_link.py`, `host_start_string_builder.py`, `inside_docker_app/main.py`. Use `dev_project.config`, `dev_project.git`, and `dev_project.project_env` instead.
- **Container configuration is file-based only.** Compose mounts `.odpm/runtime/config.json` and sets `ODPM_CONFIG_PATH`. The `ODPM_CONFIG_B64` environment variable path is removed.
- **Compose odoo service uses an exec-form entrypoint:** `python3 -m dev_project.inside_docker_app.run_odoo`. Shell one-liners (`bash -c 'cd && odoo-bin …'`) are no longer generated for the standard odoo path.
- **Removed CLI flag `--pip-install`.** Python dependencies are installed during container bootstrap from `requirements_txt` in `odpm.json` and merged transitive requirements.
- **Removed `Config.config_dict` and related legacy host configuration helpers.**
- **Removed legacy docker-compose template placeholders:** `{START_STRING}`, `{MAPPED_VOLUMES}`, `{DEBUGGER_PORT_MAP}`, and embedded `healthcheck:` blocks. Outdated project templates are auto-renamed to `deprecated_*` when detected.
- **Pre-commit** runs via `python3 -m dev_project.inside_docker_app.run_pre_commit` instead of `/bin/bash -c`.

### Added

#### Architecture and orchestration

- **`OdpmPipeline`** — host-side entry orchestrating setup, prepare, optional CI image build, VS Code configuration, and compose up.
- **`ProjectMaterializer`** — dedicated prepare phase (git, templates, runtime config, compose generation) separated from container startup.
- **`Config` decomposition** — bootstrap phases, typed configuration slices (`UserSettingsState`, `ProjectSettingsState`, `DockerLayoutState`), thin facade (~150 lines).
- **`HostProjectContext`** and **`HostRuntimeState`** — read-only project snapshot and runtime compose state decoupled from JSON manifest.
- **`subprocess_runner`** — host subprocess calls with explicit `cwd=`; global `os.chdir` removed from the host path.
- **Custom exception hierarchy** (`PipelineError`, `ConfigError`, `GitError`, …) replacing scattered `sys.exit` calls.

#### Host ↔ container contract

- **`ContainerConfig` schema v1** with JSON reference schema, stdlib validation, and legacy v0 migration.
- **Runtime config file** `.odpm/runtime/config.json` (mounted on developer/server) or baked into CI images.
- **`ComposeServiceBuilder`** and **`StartCommand`** — structured exec-form compose commands instead of string-built shell pipelines.

#### Scenarios and policy

- **`ScenarioPolicy`** and third scenario **`ci`** (in addition to existing `developer` and `server`), selected via `ODPM_SCENARIO` in `.env`.
- Explicit **`HOST_USER` / `CONTAINER_USER`** identity handling per scenario.
- **`dev_mode` policy** (`dev_project/dev_mode.py`): Odoo `--dev` only in `developer`; ignored on `server`/`ci` with a warning; auto-adds `inotify` when `reload` or `all` is set.
- **`debugpy`** gated to the developer scenario only.
- **Venv modes:** `fresh` (developer/server) vs `baked` (ci) via `ScenarioPolicy.venv_mode`.

#### Git, dependencies, reproducibility

- **`.odpm/deps.lock.json`** (schema v1) and **`--update-lock`** — pin platform, developing project (remote git), and the full resolved dependency graph.
- **`--no-git-update`** — offline prepare using existing local repositories without fetch/checkout updates.
- **`DepsLockManager`** — load, apply, collect, verify, and save dependency locks; strict verification in CI scenario.
- **Enhanced dependency discovery** when `use_oca_dependencies` is enabled: `oca_dependencies.txt`, nested `odpm.json` at dependency roots, BFS transitive resolution via `dependency_resolver.py`; version compatibility checks (warn in developer, error in CI).

#### Distribution and developer experience

- **pip package** with console script **`odpm`** (`pyproject.toml`); legacy `odpm.py` copy mode still supported via `program_dir` resolution.
- **Plan (dry-run)** — `odpm plan` previews prepare and runtime steps without git materialization, writing runtime config or root compose, or `docker compose up`; `--plan` remains as a deprecated alias. Step outcomes (`run`, `update`, `noop`, `skip`) with reasons; optional compose stack probe for `compose.up` and `--force-recreate` prediction; `--plan-no-docker`, `--plan-show-diff` (unified diffs for runtime config, compose, dockerignore), `--plan-format json` (stdout for scripting), `--plan-strict` (non-zero exit when required steps would change). Table output is logged; JSON is printed to stdout. Plan mode does not upgrade templates under `.odpm/` (a normal `odpm` run still syncs them). Unless `--plan-no-docker` is set, odpm may probe the local compose stack to predict `compose.up`.
- **Non-interactive mode** — documented CI/script workflow when stdin is not a TTY.
- **`.dockerignore` workflow** — template in `.odpm/dockerignore`, regenerated at project root on each run.
- **Template auto-upgrade** — marker-based detection; outdated templates renamed to `deprecated_*`.

#### Module decomposition

- **Host:** `git/` package (`GitRepoCoordinator`, operations, deps lock), `project_env/` package (templates, compose, CI image, links, volume mapper, symlink manager).
- **Container:** `odoo_checker/` package (database, admin, i18n, SQL), `run_odoo`, `run_pre_commit`, library-only `container_bootstrap`.
- **CI image build** — `Dockerfile.ci`, baked runtime config in build context, `odpm --build-image` (ci scenario only).

#### Quality assurance

- **544 tests** in `unittest discover` (5 skipped opt-in Docker integration tests by default).
- **Plan-safe setup** — `odpm plan` loads configuration without upgrading `.odpm/` templates; normal runs still sync project templates on startup.
- **Stale odoo.conf recovery** — `odpm --skip-start` regenerates project `odoo.conf` when Docker DB settings are missing (for example after upgrading from layouts that never wrote `db_host`).
- **`dev_project/prepare/` package** — prepare-phase registry split from monolithic `prepare_registry.py`; shim re-exports preserve existing imports and test patch paths.
- **`dev_project/host_cli/` package** — host argparse and CLI flag constants moved from `inside_docker_app`; shim re-exports preserve container `cli_params` and backward-compatible imports.
- **GitHub Actions CI** (`.github/workflows/ci.yml`) — unit suite on every push/PR to `4.0-beta` and `main` (Python 3.10 and 3.12); manual re-run via **workflow_dispatch**.
- **Opt-in Docker integration tests:** CI image build, golden-path compose + HTTP 200 (`ODPM_RUN_DOCKER_INTEGRATION=1`).
- **Scripts:** `scripts/verify_ci_scenario.sh`, `scripts/run_golden_path_test.sh`, `scripts/verify_dev_mode_flags.sh`, `scripts/verify_dev_mode_autoreload.sh`.

### Changed

- Runtime configuration is written to `.odpm/runtime/config.json` on the host (developer/server) or embedded in CI images.
- Git materialization and platform build-date handling centralized in `GitRepoCoordinator`.
- Dependency resolution is a single-pass BFS via `DependencyMaterializer` and `dependency_resolver.py`.
- Compose stack may start without `--force-recreate` when the existing stack is healthy (`compose_runtime`).
- Deprecated project artifacts (`config.json`, old compose/dockerfile markers) are renamed to `deprecated_*` with warnings.
- Unified host logging in `dev_project.logging` (container re-export shim retained temporarily).

### Removed

- CLI flag `--pip-install`.
- Legacy shims and helpers listed under Breaking Changes.
- Base64 container config bootstrap (`ODPM_CONFIG_B64`).
- Default compose healthcheck block in the project template.
- Global `ODOO_SRC_DIR` workflow from the 4.0 documented model (platform checkout managed under `ODOO_PROJECTS_DIR`).

### Migration Guide (3.x → 4.0)

1. **Install odpm 4.0** (requires Python ≥ 3.10; on PEP 668 systems use a venv or `pipx`)
   ```bash
   pip install /path/to/odoo_dev_project
   # or editable:
   pip install -e /path/to/odoo_dev_project
   odpm --version
   ```
   Legacy mode: copy `odpm.py` and `dev_project/` from the `4.0-beta` branch.

2. **Regenerate project artifacts** from your odpm project directory:
   ```bash
   odpm --skip-start
   ```
   Or run `odpm` without `--skip-start` to regenerate and start containers.

3. **Review generated `docker-compose.yml`:**
   - Odoo `command` must be exec form with `run_odoo`.
   - Environment must include `ODPM_CONFIG_PATH=/run/odpm/config.json` with a read-only mount of `.odpm/runtime/config.json`.
   - No `{START_STRING}`, `{MAPPED_VOLUMES}`, or `{DEBUGGER_PORT_MAP}` placeholders.

4. **Remove imports of deleted shims** from custom scripts.

5. **Python dependencies:** list them in `odpm.json` → `requirements_txt`. Do not use `--pip-install`.

6. **CI scenario:** set `ODPM_SCENARIO=ci` in `.env`, run `odpm --build-image`, commit `.odpm/deps.lock.json` after `odpm --update-lock` when git dependencies change.

7. **Lock file:** for teams using pinned dependencies, run `--update-lock` once and commit `.odpm/deps.lock.json`.

See also [CHANGELOG-RU.MD](CHANGELOG-RU.MD) for the Russian version.

---

## [3.0.0] - 2023-01-11

This section documents the **3.x line** retroactively (branch `3.0`, active development through 2026). No separate changelog was maintained before 4.0; the entry below is derived from the codebase and git history.

### What odpm 3.0 was

odpm 3.0 is a **local Odoo development environment manager**: one command prepares Docker, clones Odoo and addon repositories, builds a Python virtual environment inside the container, generates VS Code debugger settings, and starts Odoo. The project manifest `odpm.json` in the developing repository describes platform version, dependencies, and Python requirements.

### Architecture (3.0)

- **Procedural entry point** — all prepare steps inline in `odpm.py` (~55 lines), then `os.chdir` and `os.system("docker compose up …")`.
- **Monolithic modules** — `host_config.py` (~490 lines), `host_project_env.py` (~430 lines), single `check_odoo.py` (~270 lines).
- **Configuration passed to the container as base64 JSON** embedded in a bash shell command (`StartStringBuilder` → `{START_STRING}` in compose).
- **29 Python modules** in `dev_project/`; **no automated test suite** in the repository.
- **Two usage scenarios:** `developer` (default) and `server` (restricted Postgres/debugger exposure). No dedicated `ci` scenario.

### Added (functional capabilities in 3.x)

#### Project setup

- **`--init`** with git URL, SSH URL, or `file://` local path; **`--branch`** for the developing project.
- **Manifest files:** `odpm.json` (project/platform/deps) and `user_settings.json` (per-developer preferences).
- **Init-time parameters:** `--odoo-version`, `--odoo-git-link`, `--platform-name`, `--python-version`, `--distro-name`, `--distro-version`, `--postgres-version`, `--requirements-txt`.
- **Auto-generated Dockerfile** for Debian (11/12/13) and experimental Ubuntu (20.04/22.04).
- **Auto-detection** of Odoo subprojects/modules; automatic `odoo.conf` updates.

#### Docker and environment

- **docker-compose.yml generation** with Postgres bind volume for data persistence.
- **Usage scenarios** `developer` and `server` stored in `.env` as `ODPM_SCENARIO`.
- **`.env` configuration:** ports, backup directory, projects directory, SSH key path, gevent port.
- **System checks:** git, docker, docker-compose, free disk space, busy ports, docker group GID.
- **`--build-image`** for building a project Docker image (simpler flow than 4.0 CI scenario).

#### Git and dependencies

- Clone/update platform Odoo, developing project, and `dependencies` from `odpm.json`.
- **`--odoo-build-date`** for nightly platform checkout by date.
- Alternative Odoo source download (nightly archive) when cloning is impractical.
- **Experimental `use_oca_dependencies`:** read `oca_dependencies.txt` and pull OCA dependency repositories.
- **Experimental `create_module_links`:** symlinks into `odoo/addons` for IDE import resolution.
- Scan Python `external_dependencies` from Odoo module manifests.

#### Odoo developer CLI (host flags → container)

- Database and modules: `-d`, `-i`, `-u`, `-t` / `--test`, `--screencasts`.
- **`--odoo-bin`** passthrough for arbitrary odoo-bin arguments.
- **`scaffold`** subcommand for module generation from templates.
- Database tools: `--get-dbs-list`, `--db-backup`, `--db-restore`, `--db-drop`.
- Translations: `--translate`, **`--export-po-files`**.
- **`--set-admin-pass`**, **`--sql-execute`**, **`--start-precommit`**.
- PostgreSQL readiness waiter; restore waiter for database operations.
- Odoo **19.0** support (services model, export po, translate fixes).

#### Python environment

- **`--pip-install`** CLI flag to install Python packages from the host invocation.
- Virtual environment created/updated inside the container on startup.

#### IDE and documentation

- VS Code **`launch.json`** and **`settings.json`** for debugpy remote attach.
- Interactive first-run `.env` questionnaire.
- Bilingual documentation (README EN/RU) and gettext i18n.

### Limitations carried into 4.0 (addressed there)

- No reproducible git lock file, no `--no-git-update`, no `--plan`.
- No CI scenario with baked venv and structured CI image pipeline.
- No typed/versioned container configuration contract.
- Shell-based compose command and base64 config transfer.
- No pip-installable package; copy `odpm.py` + `dev_project/` manually.
- No automated regression test suite in the odpm repository.

---

## [2.0.0] and earlier

See git history on branches `2.0`, `2.5`, and `3.0` for early evolution from `config.json` to `odpm.json` and Docker-based workflows.
