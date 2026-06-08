# Changelog

All notable changes to **odpm** (Odoo Developer Project Manager) are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/).

---

## [Unreleased]

### Changed

- **`dev_project/git/runner.py`** — `GitRunner` extracts git subprocess command building and `run_checked` invocation from `GitOperations`; `GitOperations` delegates via thin `_build_git_cmd` / `_run_git` wrappers. Unit tests cover SSH argv, default cwd, and explicit cwd.
- **`dev_project/git/clone.py`** — `RepoCloneService` extracts clone lifecycle (`check_project`, `force_clone_repo`, `clone_repo`, `check_repo_url`) from `GitOperations`; `GitOperations` delegates via thin wrappers. Isolated unit tests cover URL normalization, clone cwd, platform shallow clone, and `check_project` without `chdir`.
- **`dev_project/git/checkout.py`** — `CheckoutService` extracts checkout orchestration (`checkout*`, `switch_to_branch`, low-level `_git_*`) from `GitOperations`; `GitOperations` delegates via thin wrappers. `apply_build_date` uses `CheckoutService.ensure_branch_exists`. Isolated unit tests cover pull-skip on pinned commit, hard `switch_to_branch`, `checkout_repository` sync flags, and explicit-commit fetch.
- **`dev_project/git/build_date.py`** — `BuildDateResolver` extracts odoo build-date resolution (`resolve_head_sha`, `resolve_commit_by_build_date`, `fetch_history_for_build_date`, `resolve_commit_with_fetch`, `apply_build_date`) from `GitOperations`; `GitOperations` delegates via thin wrappers. `apply_build_date` uses `CheckoutService.ensure_branch_exists`; `resolve_commit_with_fetch` keeps the `link._fetch_history_for_build_date` callback. `BuildDateResolverTests` added; `test_git_build_date` scenarios unchanged.
- **`dev_project/git/link.py`** — `HandleOdooProjectLink` composes `GitRunner`, `RepoCloneService`, `CheckoutService`, and `BuildDateResolver` via `_wire_git_services()`; **`dev_project/git/operations.py` removed**. Public link API unchanged; partial-link test helpers call `_wire_git_services()`. `HandleOdooProjectLinkGitServicesTests` replace `GitOperationsTests`.
- **`dev_project/config/manifests/`** — `UserSettingsReader` and `OdpmJsonReader` extract manifest path setup and JSON load from the former `ConfigLoader` facade; `odpm_json_writer.rewrite_odpm_json` writes default manifests. `OdpmJsonReaderTests`, `UserSettingsReaderTests`, and `OdpmJsonWriterTests` in `test_host_config`.
- **`dev_project/config/defaults/factory.py`** — `ConfigDefaultsFactory` extracts `get_developing_project_link`, `create_default_user_setting_json_content`, and `create_default_odpm_json_content` (including interactive Odoo version prompt); wired via `ConfigBootstrapContext.defaults` and manifest reader callbacks. `ConfigDefaultsFactoryTests` in `test_host_config`; `test_noninteractive_init` patches `defaults.factory`.
- **`dev_project/config/artifacts/deprecated.py`** — `DeprecatedConfigHandler` extracts legacy `config.json` migration and deprecated template placeholder scanning; wired via `ConfigBootstrapContext.deprecated` in bootstrap and layout. `DeprecatedConfigHandlerTests` in `test_host_config`; `test_template_upgrade` unchanged.
- **`dev_project/config/transforms/`** — `beautify_module_list` and `OdooBuildDateResolver` extract module-list normalization and build-date resolution; bootstrap wires transforms via `ConfigBootstrapContext.build_date` and direct `beautify_module_list` import. `ConfigTransformsTests` in `test_host_config`.
- **`dev_project/config/bootstrap_context.py`** — `ConfigBootstrapContext` replaces `ConfigLoader` as composition root for manifests, artifacts, defaults, and transforms; bootstrap and layout call context services directly; public `rewrite_odpm_json()` delegates to `odpm_json_writer`. **`dev_project/config/loader.py` removed**. `ConfigBootstrapContextWiringTests`, `BindDevelopingLinkTests`, `BindPlatformLinkTests`; bootstrap slice tests assert context service calls; `config._loader` mocks removed from tests.
- **`dev_project/config/bootstrap_context.py` (C-6)** — `ConfigPaths`, `OdooConfBuilder`, and `GitRepoCoordinator` wired in `ConfigBootstrapContext`; `init_context` aliases `config._paths` / `_odoo_conf` / `_git_repos` from context; `layout` uses `ctx.paths` and `ctx.odoo_conf`; `GitRepoCoordinator` receives injected `paths` and `bind_platform_link` callback. `ConfigBootstrapContextWiringTests` host-services test; `config._git_repos` mocks removed from `test_git_repos`.
- **`dev_project/project_env/services/platform_sources.py`** — `PlatformSourcesService` extracts `download_odoo_nightly_build` from `CreateProjectEnvironment`; `SystemChecker.check_file_system` wires nightly download for server scenario. Developer platform git clone runs in prepare `git.materialize` via `materialize_git_repos`. `PlatformSourcesServiceTests` in `test_project_env_links`.
- **`dev_project/project_env/services/platform_sources.py` (R-1)** — removed unused `download_odoo_repository` (hardcoded `ODOO_GIT_LINK` clone with no production callers); use `get_platform_sources` or `download_odoo_nightly_build`.
- **`dev_project/project_env/services/vscode_configurator.py`** — `VscodeConfigurator` extracts VS Code boundary (`get_vscode_dir_path`, `build_debugger_path_mappings`, `update_vscode_debugger_launcher`, `generate_vscode_settings_json`) from `ProjectTemplates`; `RuntimeCoordinator.configure_vscode` calls the service directly. `VscodeDebuggerMappingsTests` target the service.
- **`dev_project/project_env/services/ci_image_build.py`** — `CiImageBuildService` extracts CI image build orchestration over `CiImageBuilder`; `RuntimeCoordinator.handle_build_image` calls the service directly. `CiImageBuildServiceTests` in `test_project_env_modules`; pipeline tests patch `CiImageBuildService`.
- **`dev_project/project_env/services/docker_base_image.py`** — `BaseImageService` extracts base image orchestration over `BaseImageBuilder`; `SystemChecker.check_docker` and `CiImageBuilder.build_ci_image` call the service directly. `BaseImageServiceTests` in `test_project_env_modules`; `test_phase2_infra` patches `BaseImageService`.
- **`dev_project/project_env/environment.py` (E-5)** — `CreateProjectEnvironment` slimmed to prepare wiring only (`templates`, `compose_generator`, `links`, `mapped_folders`, system-checker attachment); runtime delegates removed. Post-prepare runtime lives in `RuntimeCoordinator` and `project_env.services`.
- **`dev_project/runtime_coordinator.py` (E-6)** — `RuntimeCoordinator` owns post-prepare runtime (CI build, VS Code, compose up) via `run_after_prepare`; `OdpmPipeline` delegates through thin wrappers. `RuntimeCoordinatorPolicyTests` and `RuntimeCoordinatorComposeTests` in `test_odpm_pipeline`; pipeline orchestration under 150 LOC.
- **P2 cleanup** — `RuntimeProjectServicesProtocol` removed; bootstrap phase functions moved to `config/bootstrap_phases.py` (`bootstrap.py` <100 LOC); server nightly download via `PlatformSourcesService`; CHANGELOG E-1…E-4 bullets corrected.
- **`dev_project/check_system.py` (R-2)** — developer platform clone is owned by prepare `git.materialize` (`materialize_git_repos`); init `check_file_system` only validates and logs when the platform repo is not ready yet. `test_phase2_infra` and `test_prepare_context` updated.
- **`dev_project/check_system.py` (R-3)** — server scenario platform nightly download uses `stdin_is_interactive` / `prompt_input`; non-interactive runs fail fast with `NON_INTERACTIVE_SERVER_PLATFORM_MISSING` instead of blocking on `input()`. README EN+RU server/non-interactive sections updated.
- **CI policy (R-4)** — README EN+RU **CI matrix**: `compose-smoke` (minimal fixture [`tests/fixtures/minimal_odpm_project/`](tests/fixtures/minimal_odpm_project/)) is the PR merge gate; full `golden-path` is opt-in (nightly, `workflow_dispatch`, PR label `run-docker`, secret `ODPM_GOLDEN_PATH_PROJECT`). Maintainer comments in `.github/workflows/ci-docker.yml`; `goals_ru.md` #5 updated; `docs/smoke-4.0-checklist.md` and post-audit plan baseline synced. Documented test count **634** passed.

---

## [4.1.0] - 2026-06-06

Minor release that completes the package layout started in 4.0: **root import shims are removed**. Use canonical paths under `dev_project.prepare`, `dev_project.plan`, `dev_project.compose`, and `dev_project.host`.

### Breaking Changes

- **Removed root import shims.** The following modules no longer exist; import from the canonical package paths instead (see Migration Guide 4.0→4.1 below and README **Migration 4.0→4.1 imports**):
  - `dev_project.prepare_registry` → `dev_project.prepare`
  - `dev_project.plan_compose_preview`, `plan_runtime_preview`, `plan_compose_runtime`, `plan_diff`, `plan_format`, `plan_cli` → `dev_project.plan.*`
  - `dev_project.compose_service_builder`, `compose_runtime`, `compose_command_render`, `start_command` → `dev_project.compose.*`
  - `dev_project.host_context`, `host_runtime`, `host_user_env`, `host_cli/*` → `dev_project.host.*` / `dev_project.host.cli.*`
  - `dev_project.project_env.compose` → `dev_project.compose.ComposeGenerator` (from `dev_project.compose.generator`)
  - `dev_project.inside_docker_app.cli_params`, `inside_docker_app.parse_args` → container checker uses `inside_docker_app.params`; host CLI uses `dev_project.host.cli.*`
- **`DeprecationWarning` on shim import is gone** — shims no longer exist; stale imports fail with `ModuleNotFoundError`.

### Changed

- **Production and tests use canonical imports only.** `CreateProjectEnvironment` imports `ComposeGenerator` from `compose.generator`; compose template upgrade uses `project_dir_manager.template_needs_upgrade`.
- **Container checker CLI flag names** live in `dev_project.inside_docker_app.params` (no host-package dependency).
- **590 tests** in `unittest discover` (7 skipped opt-in Docker integration tests); shim deprecation and duplicate shim smoke tests removed.

### Migration Guide (4.0 → 4.1)

If you already migrated imports when 4.0 shims emitted `DeprecationWarning`, **no further action is required**.

1. **Replace any remaining root shim imports** in custom scripts, CI, or forked modules. Use the mapping table in README **Migration 4.0→4.1 imports** (same paths as the 4.0 deprecation messages).
2. **Typical replacements:**
   ```python
   # Before (4.0 shim — removed in 4.1)
   from dev_project.prepare_registry import make_prepare_context
   from dev_project.host_cli.args import OdpmCliArgs
   from dev_project.project_env.compose import ComposeGenerator

   # After (4.1 canonical)
   from dev_project.prepare import make_prepare_context
   from dev_project.host.cli.args import OdpmCliArgs
   from dev_project.compose.generator import ComposeGenerator
   ```
3. **Re-run your extension tests** after updating imports; `@patch` targets must use canonical module paths (e.g. `dev_project.compose.generator.template_needs_upgrade`, not `dev_project.project_env.compose.*`).

See also [CHANGELOG-RU.MD](CHANGELOG-RU.MD) for the Russian version.

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

- **597 tests** in `unittest discover` (7 skipped opt-in Docker integration tests by default).
- **Plan-safe setup** — `odpm plan` loads configuration without upgrading `.odpm/` templates; normal runs still sync project templates on startup.
- **Stale odoo.conf recovery** — `odpm --skip-start` regenerates project `odoo.conf` when Docker DB settings are missing (for example after upgrading from layouts that never wrote `db_host`).
- **`dev_project/prepare/` package** — prepare-phase registry split from monolithic `prepare_registry.py`; shim re-exports preserve existing imports and test patch paths.
- **`dev_project/host/` package** — host context, runtime state, user `.env`, and CLI (`host/cli/`); legacy `host_cli/` and `host_*.py` import paths remain as shims.
- **`dev_project/compose/` package** — compose service builder, start command, YAML render, generator, and runtime helpers; legacy `compose_*.py`, `start_command.py`, and `project_env.compose` import paths remain as shims.
- **`dev_project/plan/` package** — plan core types, planner, CLI helpers, formatters, diffs, and compose/runtime preview; legacy `plan_*.py` import paths remain as shims.
- **`OdpmCliArgs` typed CLI** — frozen dataclass with `from_namespace` bridge and `parse_cli_args()`; host pipeline (`OdpmPipeline`, prepare/plan/config paths) uses `OdpmCliArgs` end-to-end; `Namespace` remains only in `parse_args()` and container dispatch shim.
- **Native `odpm plan` subparser** — shared argparse parent parser; `odpm plan --skip-start` parses without argv rewrite; global `--plan` remains a deprecated alias with a warning.
- **GitHub Actions CI** (`.github/workflows/ci.yml`) — unit suite on every push/PR to `4.0-beta` and `main` (Python 3.10 and 3.12); manual re-run via **workflow_dispatch**.
- **GitHub Actions Docker CI** (`.github/workflows/ci-docker.yml`) — compose smoke on every push/PR (`odpm --skip-start` on minimal fixture + `docker compose config`); full golden-path nightly, on **workflow_dispatch**, or PR label `run-docker`.
- **Opt-in Docker integration tests:** CI image build, golden-path compose + HTTP 200 (`ODPM_RUN_DOCKER_INTEGRATION=1`).
- **Scripts:** `scripts/verify_ci_scenario.sh`, `scripts/run_compose_smoke_test.sh`, `scripts/run_golden_path_test.sh`, `scripts/verify_dev_mode_flags.sh`, `scripts/verify_dev_mode_autoreload.sh`.

### Changed

- Runtime configuration is written to `.odpm/runtime/config.json` on the host (developer/server) or embedded in CI images.
- Git materialization and platform build-date handling centralized in `GitRepoCoordinator`.
- Dependency resolution is a single-pass BFS via `DependencyMaterializer` and `dependency_resolver.py`.
- Compose stack may start without `--force-recreate` when the existing stack is healthy (`compose/runtime`).
- Deprecated project artifacts (`config.json`, old compose/dockerfile markers) are renamed to `deprecated_*` with warnings.
- Unified host logging in `dev_project.logging` (container re-export shim retained temporarily).
- **Developer port release decoupled from `check_system`.** New prepare step `docker.ports.release` always runs in the developer scenario before compose and stops containers occupying configured odoo/debugger/postgres/gevent ports; `docker.engine.check` (git/docker beginner checks) remains gated by `check_system`.
- **Production imports use canonical package paths.** `ProjectMaterializer`, `OdpmPlanner`, `prepare/execute`, and `plan/runtime_preview` import from `dev_project.prepare`, `dev_project.git.deps_lock_manager`, and `dev_project.plan.compose_preview` instead of root shims `prepare_registry`, `plan_compose_preview`, and `plan_runtime_preview`.
- **Unit tests patch canonical modules.** Migrated `@patch` targets from root shims (`prepare_registry`, `compose_runtime`, `plan_format`, …) to `dev_project.compose.*`, `dev_project.plan.*`, `dev_project.prepare.*`, and `dev_project.config.payload`; supporting call sites in compose/plan/prepare packages now resolve stack health and runtime config without self-shim hops.
- **Plan preview layer unified.** `preview_runtime_config_text` and `prepare_runtime_config_for_compose_preview` live in `plan/compose_preview.py`; `plan/preview.py` re-exports compose and runtime preview helpers. `prepare/steps_compose.py` and `prepare/runtime.py` import canonical plan/compose modules directly (no `prepare_registry` in `prepare/`).
- **`SystemCheckPolicy` centralizes host check gating.** New `dev_project/system_check_policy.py` defines `beginner_git`, `beginner_docker`, `developer_port_release`, `compose_validate`, and `file_system_on_init`; `SystemChecker`, prepare docker steps, and pipeline setup read the policy instead of ad-hoc `check_system` / scenario checks.
- **Root shim imports emit `DeprecationWarning`.** Backward-compatible modules (`prepare_registry`, `plan_*`, `compose_*`, `host_*`, `host_cli/*`, `inside_docker_app/cli_params`, `inside_docker_app/parse_args`, `project_env.compose`) warn on import with the canonical replacement path; see README section **Migration 4.0→4.1 imports**. Shims are removed in 4.1.0.
- **`PrepareContext` injects prepare services.** `ProjectTemplates`, `ComposeGenerator`, and `ProjectLinks` are wired in `make_prepare_context` from `CreateProjectEnvironment` (or built for plan-only/mocked envs).
- **Prepare steps call injected services directly.** Template, compose, and project prepare steps execute via `ctx.templates`, `ctx.compose_generator`, and `ctx.links`; compose preview reads volume map and generator from the same context. Git checkout uses `ctx.links`.
- **`CreateProjectEnvironment` is runtime-only; protocols split.** Prepare operations live on `ProjectTemplates`, `ComposeGenerator`, and `ProjectLinks`; `CreateProjectEnvironment` implements `RuntimeProjectServicesProtocol` only (`PrepareProjectServicesProtocol` documents the prepare surface). Removed prepare delegate methods from `CreateProjectEnvironment`.

### Fixed

- **`check_system: false` no longer skips port cleanup.** Regression after plan-safe docker check: occupied host ports (for example PostgreSQL on 5432) caused `compose up` bind failures when switching between odpm projects with `check_system` disabled.
- **Subprocess failures no longer silent on required commands.** Added `SubprocessError` and `run_or_raise()`; system checks and base image probe use fail-loud semantics; `docker container ls` errors surface as `SystemCheckError` during port release.

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
