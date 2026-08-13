# История изменений

Здесь описаны значимые изменения **odpm** (Odoo Developer Project Manager) — инструмента, который по описанию проекта в файле `odpm.json` разворачивает окружение для разработки на платформе Odoo: клонирует исходники, собирает Docker-образ, поднимает PostgreSQL и Odoo, настраивает отладчик в VS Code.

Формат ориентирован на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/), но текст написан развёрнуто — для тех, кто не следил за внутренней историей репозитория.

---

## [Unreleased]

### Добавлено

- **Compose `privileged` / `pid` на sidecar (4.7+)** — whitelist `privileged` (boolean) и `pid` (строка, напр. `host` / `service:<name>`) в manifest `services` / `service_patches` (schema + passthrough + `${VAR}` / `${@service:}` / `${@secret:}` в `pid`); structural checks. Тесты: `test_manifest_v2_reader`, `test_env_substitution`, `test_compose_validate`, `test_compose_fragments`. Документация: `odpm-json.md`, `plugins.md`, ADR-009.
- **Compose `hostname` / `healthcheck` на sidecar (4.7+)** — whitelist `hostname` и Compose-shaped `healthcheck` в manifest `services` / `service_patches` (schema + passthrough + `${VAR}` / `${@service:}` / `${@secret:}` в строках); structural checks. Тесты: `test_manifest_v2_reader`, `test_env_substitution`, `test_compose_validate`, `test_compose_fragments`. Документация: `odpm-json.md`, ADR-009.
- **Бэкенды сборки CI-образа (4.7+)** — сменные `docker` (по умолчанию) и `kaniko` для `odpm --build-image`; CLI `--image-builder` / `--image-push` и env `ODPM_CI_IMAGE_BUILDER` / `ODPM_CI_IMAGE_PUSH` / настройки Kaniko executor; ADR-016. Тесты: `test_ci_image_build_backends`. Документация: `ci.md`, `cli.md`, `env-dotenv.md`.
- **Manifest `odoo_conf`: доп. секции INI (4.7+)** — рядом с `options` можно объявлять секции модулей (`redis_server`, `s3_server`, …); schema + deep merge + `${@secret:}` / `${@service:}`. Reserved keys только в `options`. Тесты: `test_manifest_odoo_conf`, `test_odoo_conf_builder`. Документация: `odpm-json.md`, `odoo-conf.md`.
- **`${@secret:<ключ>}` в manifest (4.7+)** — подстановка значений из `.odpm/secrets.json` в `services` / `service_patches` / hooks / `odoo_conf` (ключи с точкой); нужен файл секретов или `--secrets-file` (импорт до Config bootstrap); заглушки отклоняются; осознанный дубль в generated compose YAML для sidecar. Тесты: `test_env_substitution`, `test_secret_refs`, `test_odpm_pipeline`. Документация: `odpm-json.md`, `secrets.md`, `plugins.md`.
- **`${@service:<имя>}` в compose-полях (4.7+)** — logical имена сервисов (`db`, `odoo`, sidecars) раскрываются в physical с учётом `ODPM_COMPOSE_PREFIX` / `POSTGRES_SERVICE_NAME` в whitelist `services` / `service_patches` (`environment`, `command`, …) и argv hooks; поправка ADR-012. Документация: `docs/reference/odpm-json.md`, `docs/reference/env-dotenv.md`. Тесты: `test_env_substitution`, `test_compose_service_prefix`, `test_compose_service_names`.
- **Manifest `service_sources` (4.7+)** — именованные git-ссылки для sidecar/build-контекстов в manifest v2; prepare `sources.materialize` клонирует в `${ODOO_PROJECTS_DIR}/service-sources/<name>`; подстановка `${@source:<name>}` и env `ODPM_SOURCE_*`; валидация `services.*.source`; map `service_sources` в `deps.lock.json`; не попадает в `addons_path`. ADR-015. Документация: `docs/reference/service-sources.md`. Тесты: `test_service_sources_manifest`, `test_service_sources_materialize`, `test_service_sources_lock`, `test_service_sources_addons_path`, расширенный `test_env_substitution`.
- **Manifest `secrets.required` (4.7)** — блок `secrets` в manifest v2 (и scenario overlays): обязательные ключи в `.odpm/secrets.json`; предупреждения на `odpm manifest validate` и `odpm plan`; остановка до compose при `required: true` и отсутствующих/заглушечных секретах. Тесты: `test_manifest_secrets_policy`.
- **Scenario overlay `hooks` и `dependencies` (4.7)** — lifecycle hooks и дополнительные git-зависимости в `scenarios.*`; merge с корнем (hooks — append по фазам; dependencies — append + dedupe как у `requirements`); effective slice в `ManifestView.hooks`, flat `dependencies` и шаги `odpm plan`. Поправка ADR-011. Тесты: `test_manifest_scenario_overrides`, `test_manifest_v2_reader`, `test_manifest_hooks`, `test_scenario_plan_matrix` (A18b).

### Изменено

- **Сценарий server клонирует platform через git** — как `developer`: prepare `git.materialize`; убрана legacy-загрузка nightly zip (`PlatformSourcesService`), хелперы free-space/Yandex Disk и `get_platform_sources`. Фиксация версии — `odoo_build_date` / `--odoo-build-date`. Документация: `docs/scenarios/server.md`, `docs/operations/non-interactive.md`.
- **Golden-path CI ≤9 мин** — job `timeout-minutes: 9` в `release-packages.yml` / `ci-docker.yml`; refresh с `ODPM_GOLDEN_PATH_AUTO_REMEDIATE=1` (remedi ate при несовместимой схеме: `base` 19.x + `web`, и `res_lang.short_time_format` только если смонтированный Odoo ещё объявляет поле); HTTP wait `ODPM_GOLDEN_PATH_TIMEOUT=60`. Установка `.deb`: `sudo -n` fail-fast + `timeout 60` (без `-E`: узкий sudoers без SETENV); шаблон узкого NOPASSWD `scripts/ci/github-actions-runner-sudoers.example`. Документация: `docs/contributing/ci.md`, ADR-006.
- **Новые проекты:** в `user_settings.json` по умолчанию `create_demo: false`.
- **Сценарий server:** в compose для `db` и `odoo` задаётся `restart: unless-stopped` (переживает перезагрузку хоста).

## [4.7.0-beta] - 2026-06-23

**Pre-release 4.7.0-beta** на ветке `4.7.0-dev`; stable-линия остаётся **4.6.0** (`LATEST_STABLE_RELEASE`). Scenario overlays в manifest, префикс compose-стека, layered `.env` на хосте, compose-сеть стека. Без breaking changes для flat v1 `odpm.json`; возможности 4.7 по-прежнему opt-in.

### Добавлено

- **Per-scenario overlays в manifest (4.7)** — необязательный блок `scenarios.developer` / `server` / `ci` в manifest v2 для `odoo_conf`, `services`, `service_patches` и `requirements` по сценарию; effective slice при load и `odpm manifest validate`; runtime wire в `odoo.conf`, requirements, compose fragments и plan preview. ADR-011. Тесты: `test_manifest_scenario_overrides`, расширения `test_manifest_v2_reader`, `test_compose_fragments`, `test_scenario_plan_matrix`.
- **Префикс compose-стека из `.env` (4.7)** — необязательный `ODPM_COMPOSE_PREFIX` для полной изоляции стека: физические ключи сервисов (`{prefix}db`, `{prefix}odoo`), том postgres, имя проекта Docker Compose (`-p` / `name:` в YAML), автоматическое переписывание `depends_on` и manifest sidecars; без префикса — прежний `POSTGRES_SERVICE_NAME`. Runtime CLI и снимок database drift включают physical names и `compose_project_name`. ADR-012. Тесты: `test_compose_service_names`, `test_compose_service_prefix`, `test_compose_runtime`, `test_compose_exec`, `test_database_drift`.
- **Compose-сеть стека из `.env` (4.7)** — необязательные `ODPM_COMPOSE_NETWORK` / `ODPM_COMPOSE_NETWORK_EXTERNAL` для одной именованной сети (managed bridge или external proxy) на весь стек; без переменных — implicit default; prefix для managed; warning в `manifest validate` при `networks: ["stack"]` без matching `.env`. ADR-014. Тесты: `test_compose_network`, `test_compose_validate`, расширения `test_manifest_scenario_overrides`, `test_user_env_bootstrap`, `test_env_substitution`.

### Изменено

- **Layered `.env` на хосте (4.7)** — при чтении merge `~/.odpm/.env` (база) и project `.env` (overlay; project побеждает по ключу); write target без изменений. Ранний `ODPM_LOCALE` и `${VAR}` в manifest используют effective dict. ADR-013. Тесты: `test_user_env_bootstrap`, `test_odpm_locale_env`, `test_env_substitution`.
- **Снимок compose fragments** — `.odpm/compose/fragments/services.snapshot.json` включает `odpm_scenario`; смена `ODPM_SCENARIO` помечает fragments как stale.
- **Release gate (R7 / 4.7.0-dev)** — `RELEASE_VERSION` → `4.7.0-beta`; `LATEST_STABLE_RELEASE` остаётся `4.6.0`; CI/docs workflows на `4.7.0-dev`; deb/rpm pre-release packaging синхронизирован; install docs и documentation-versions hub указывают **4.7.0-beta** в APT/YUM **testing**.

## [4.6.0] - 2026-06-23

**Stable-релиз 4.6.0** на ветке `4.6.0-dev`; заменяет **4.5.0** как `LATEST_STABLE_RELEASE`. Debt closure D1–D5 (compose `service_patches`, config hub phase 2, plugin API 1.1, структурная валидация compose, ops hygiene) плюс compose UX в manifest и переопределения `odoo_conf`. Pre-release **4.6.0-beta** проверил packaging, каналы документации и integration-гейты. Без breaking changes для flat v1 `odpm.json`; возможности manifest v2 по-прежнему opt-in.

### Добавлено

- **Manifest v2 compose UX (4.6)** — раскрытие `${VAR}` в `services` / `service_patches` при чтении manifest; `${VAR}` в argv `hooks` при выполнении с merged subprocess env; поля `user` / `tty` у sidecar в `composeService`; документация (`plugins.md`, `odpm-json.md`), обновление ADR-009. Тесты: `test_env_substitution`, `test_manifest_hooks`, `test_manifest_v2_reader`, `test_compose_fragments`, `test_compose_validate`.
- **Переопределения `odoo_conf` в manifest (4.6)** — необязательный `odoo_conf.options` в manifest v1/v2 для командных настроек Odoo в git; политика reserved keys блокирует ключи, которыми управляет odpm (`addons_path`, `data_dir`, `db_*`, `admin_passwd`, `http_port`); приоритет merge: дисковый `odoo.conf` → manifest → odpm-managed; `${VAR}` в значениях `odoo_conf`; `odpm manifest validate` проверяет политику. Документация (`odpm-json.md`, `odoo-conf.md`), каталог i18n. Тесты: `test_manifest_odoo_conf`, `test_odoo_conf_builder`, `test_manifest_contract`.
- **Unit gate plan/dry-run** — `tests/test_scenario_plan_matrix.py`: задокументированное поведение `odpm plan` и manifest CLI без Docker daemon (сценарии `developer` / `server` / `ci`); таблица трассировки `tests/PLAN_MATRIX.md`; раздел в `docs/contributing/ci.md`.

### Исправлено

- **Ложные срабатывания `--plan-strict` на шагах compose** — флаги `plan_strict` и `plan_format` исключены из сравнения preview runtime config (`PLAN_ONLY_ARGUMENT_KEYS`): при уже материализованном runtime config `compose.service` / `compose.generate` больше не помечаются как обязательные изменения только из‑за `--plan-strict`.

### Изменено

- **Release gate (R6 / 4.6.0)** — `RELEASE_VERSION` → `4.6.0`; `LATEST_STABLE_RELEASE` → `4.6.0`; deb/rpm packaging синхронизирован; install docs и alias mike `stable` указывают на **4.6.0**.

## [4.3-rc1] - 2026-06-08

**Релизная линия 4.3-rc1; формат manifest `odpm.json` (`odpm_version`) и `odpm --version` остаются на линии 4.0.**

### Добавлено

- **VS Code `extraPaths` из графа Odoo-репозиториев** — `PythonAnalysisPathsBuilder` заполняет `python.analysis.extraPaths` в генерируемом `.vscode/settings.json` из platform, developing, зависимостей, subproject roots и venv; предпочитает относительные пути симлинков. Тесты: `test_vscode_python_paths.py`. Документация: `vscode-debug.md`, `generated-files.md`.
- **Автоустановка `odoo-stubs` в сценарии developer** — `normalize_odoo_stubs_requirements()` добавляет git-пин [odoo-ide/odoo-stubs](https://github.com/odoo-ide/odoo-stubs) по мажорной версии Odoo (≤ 18); для Odoo ≥ 19 не добавляется (встроенный typing). На server/ci удаляется, как debugger-пакеты. Тесты: `test_ide_stubs_requirements.py`, `test_scenario_policy.py`. Документация: `vscode-debug.md`.
- **Подстановка `${VAR}` в manifest (MVP)** — `${VAR}` / `${VAR:-default}` и экранирование `$$` в whitelist-полях: host `odpm.json` (`dependencies`, `odoo_git_link`), host `user_settings.developing_project`, вложенный `odpm.json` в зависимостях. `EnvResolver`: `os.environ` перекрывает project `.env`; раскрытие сразу после `json.load`. Отсутствующая переменная → локализованный `ConfigError`. В `deps.lock.json` — уже раскрытые URL/пути (тесты `test_env_substitution_lock_integration.py`). Документация RU: `odpm-json.md`, `user-settings.md`, `git-links.md`, `env-dotenv.md`, `config-hierarchy.md`, `deps-lock.md`, `non-interactive.md`, `team-coordinator.md`. i18n для ошибки missing var.
- **План architecture debt восстановлен как status doc** — `docs/contributing/architecture-debt.md` (ретроспектива G/C/E); синхронизирован `todo.md`. Локальное правило Cursor обновлено (`.cursor/` в gitignore).
- **CI secrets import smoke (TD-FEAT-09 MVP)** — `tests/test_ci_secrets_smoke.py`: `--secrets-file` → materialize → mount в compose (developer); в `ci` шаг `secrets.materialize` — `skip`. Шаг в `ci-docker.yml`. Документация: `docs/operations/secrets.md` (пример GitHub Actions).
- **Метаданные PyPI и ручной workflow публикации** — расширен `pyproject.toml` (зависимость `packaging`, GPL-3.0-or-later, URLs, classifiers); [`.github/workflows/publish-pypi.yml`](.github/workflows/publish-pypi.yml) только через `workflow_dispatch` (по умолчанию TestPyPI). Тесты: `test_pyproject_packaging.py`. Документация: `docs/contributing/packaging.md`.
- **Расширяемые debugger backends (этап 2) — `pydevd_connect` / PyCharm Debug Server** — backend `PydevdConnectBackend`: контейнер подключается к IDE через `pydevd-pycharm` (`run_with_pydevd`, in-process `runpy` после `settrace`). Compose `DEV_EXTRA_HOSTS` для `pydevd_connect`; без publish debugger-порта. `PycharmConfigurator` → `.run/Odoo Debug Server.run.xml`; wizard `connect_host` / `suspend`; preview шага `pycharm.settings` по backend. Тесты: `test_run_with_pydevd.py`, расширения compose/profile/pycharm/user_env. Документация: `vscode-debug.md`, `env-dotenv.md`, `generated-files.md`. **Примечание:** end-to-end smoke с PyCharm Pro в CI не фиксировался.
- **Расширяемые debugger backends (этап 1)** — пакет `dev_project/debugger/`: реестр с `debugpy_listen`, `resolve_debugger_backend()`, `normalize_debugger_requirements()`. В `.env`: `ODPM_DEBUGGER_BACKEND`, `ODPM_IDE`, `ODPM_DEBUGGER_CONNECT_HOST`, `ODPM_DEBUGGER_SUSPEND` (интерактивный wizard для backend/IDE в `developer`). Опциональный объект `ContainerConfig.debugger`; `run_odoo.build_odoo_exec_argv` через реестр backends. `debug-profile.json` schema v2 (`backend`, `direction`) с апгрейдом v1. `PycharmConfigurator` → `.run/Odoo Remote Attach.run.xml` (Attach to DAP); `RuntimeCoordinator.configure_ide()`; шаг плана `pycharm.settings`. Тесты и документация: `vscode-debug.md`, `generated-files.md`, `env-dotenv.md`.
- **IDE-neutral `DebuggerProfile` v1 (`profile_only`)** — `dev_project/project_env/debug_profile.py`: схема профиля отладчика, builder path mappings, запись `.odpm/runtime/debug-profile.json` при `include_debugpy` (до настройки VS Code). `VscodeConfigurator` берёт mappings и attach-параметры из профиля; symlink aliases с нормализацией `realpath`. В `odpm plan` — шаг `ide.debug_profile`, preview/diff в `plan/debug_profile_preview.py`. Тесты и документация (`vscode-debug.md`, `generated-files.md`).

### Изменено

- **`BootstrapState` (A4-2 C-7)** — bootstrap-поля (`developing_project` link, platform link, пути manifest, raw JSON, флаги загрузки) вынесены в `BootstrapState` (`config.bootstrap`); на `Config` сохранены property-shim для обратной совместимости. `developing_project` убран из user slice facade (строка остаётся в `UserSettingsState`). `bootstrap_phases` используют `config.bootstrap` внутри. Тесты: `ConfigBootstrapStateTests` в `test_host_config`.
- **`--init --branch` синхронизирует developing до чтения `odpm.json`** — если в клоне уже есть `odpm.json` (например на default branch), при указании `--branch` выполняются checkout и симлинки на проект, а не пропуск git. Исправляет ошибку версии и отсутствие symlink при повторном init. Тесты: `test_developing_repo_materializer.py`.
- **`ScenarioPolicy.skip_ide_config`** — переименовано с `skip_vscode`; отключает генерацию конфигов VS Code и PyCharm (в `ci` IDE-файлы не создаются). Свойство `skip_vscode` оставлено как read-only alias.
- **`release-packages`: артефакты на push в ветки** — workflow на push в `4.0-beta` / `4.0-rc1` / `main` (не только тег `v*` / `workflow_dispatch`); combined-артефакт Actions `release-packages` (`.deb`, `.rpm`, `SHA256SUMS`). GitHub Release — только по тегу. README EN+RU, матрица CI.
- **`VscodeConfigurator`: symlink `pathMappings`** — в `launch.json` добавляются alias-пути для симлинков в корне проекта и в `dependencies/` (тот же `remoteRoot`, что у смонтированного real path). Исправляет серые breakpoints при открытии модулей через `project/...` в дереве odpm-проекта вместо `~/odoo_projects/...`. `tests/test_vscode_debugger_mappings.py`.
- **Wizard `.env`: без вопроса про SSH-ключ** — при первом запуске wizard больше не спрашивает `PATH_TO_SSH_KEY`; в создаваемом `.env` ключ пустой, git использует обычный OpenSSH/ssh-agent. Параметр остаётся опциональным advanced override в `.env` / env. README EN+RU обновлены.
- **`ODPM_LOCALE` в `.env` (A1c / L-track)** — опциональная локаль host CLI в project `.env` или `~/.odpm/.env`; пустой ключ — система/`LANG`. `resolve_effective_locale()` + ранний bootstrap из project `.env` до cli guards; интерактивный wizard спрашивает локаль; `tests/test_odpm_locale_env.py`. README EN+RU: таблица приоритетов. Не путать с `db_lang` (язык БД Odoo).
- **Lazy import `CiImageBuildService` на host** — `project_env.services` подгружает `CiImageBuildService` (и `bake_venv`) только для `--build-image`; обычный `odpm` / `--init` больше не импортирует `bake_venv` при старте. Subprocess import test в `test_protocols_and_imports`.
- **Дефолт `check_system: true`** — новые проекты после `odpm init` и manifest без явного ключа получают beginner-проверки git/docker и `ensure_base_image` при первом запуске (исправляет пропуск сборки base image при отсутствии ключа). CI minimal fixture по-прежнему с явным `"check_system": false`. README EN+RU описывают дефолт.
- **RPM package (B2)** — `packaging/odpm.spec` (pyproject `%pyproject_*` на Fedora 41+), `packaging/rpmlint.toml`, `scripts/build_rpm.sh`, `scripts/smoke_rpm_install.sh`; [`.github/workflows/release-packages.yml`](.github/workflows/release-packages.yml) добавляет job **rpm** + **publish** (`.deb` + `.rpm` + `SHA256SUMS`). README EN+RU: установка на Fedora.
- **Debian package (B1)** — каркас `debian/` (`control`, `rules`, `changelog`, `copyright`); `scripts/build_deb.sh`, `scripts/smoke_deb_install.sh`; [`.github/workflows/release-packages.yml`](.github/workflows/release-packages.yml) собирает `odpm_*_all.deb` по тегу + `workflow_dispatch`, lintian + install smoke на Ubuntu 24.04, артефакты GitHub Release + `SHA256SUMS`. README EN+RU: **рекомендуемая установка** = `.deb` из Releases. `bake_venv` / `check_virtualenv` используют `packaging` (не `pip._vendor`); deb **Depends** на `python3-packaging`.
- **Lint CI (A2)** — gate **ruff** на `dev_project/`, `tests/`, `odpm.py`: `[tool.ruff]` в `pyproject.toml`, `scripts/lint.sh`, `.pre-commit-config.yaml` (опционально), blocking job **`lint`** в `.github/workflows/ci.yml`. Baseline: неиспользуемые импорты, `TYPE_CHECKING` для `HostProjectContext`, `raise ... from err`, `FrozenInstanceError` в тестах. README EN+RU описывают локальный lint и pre-commit.
- **`dev_project/host_summaries.py` (A1b)** — локализованные human summaries на host для prepare/compose (`log_prepare_*`, `log_starting_containers`, подсказка при ошибке compose); raw-логи контейнера без изменений (English). Каталог + `tests/test_human_summaries.py`; таблица трёх уровней i18n в README EN+RU.
- **`dev_project/translations.py` (A1)** — host CLI переведён на GNU gettext (`_()`, `set_locale()` читает `LC_ALL` / `LANG`); inline-словарь `translations` удалён. Русский каталог `dev_project/i18n/ru_RU/LC_MESSAGES/main.{po,mo}`; `package-data` включает `.mo`. `scripts/sync_i18n_catalog.py` пересобирает каталоги; `scripts/check_i18n_catalog.py` сверяет msgid в коде с таблицей ru_RU; README EN+RU описывают `xgettext` / `msgmerge` / `msgfmt`. `tests/test_translations.py` проверяет локаль `ru_RU`. По итогам аудита: `*.mo` в git, сброс локали в тестах, удалены one-shot migration scripts, очищен stub `en_US`, убраны мёртвые импорты `translations`.
- **`dev_project/git/runner.py`** — `GitRunner` вынесен из `GitOperations`: сборка git-argv (в т.ч. SSH) и вызов `run_checked`; `GitOperations` делегирует через `_build_git_cmd` / `_run_git`. Unit-тесты проверяют argv, cwd по умолчанию и явный cwd.
- **`dev_project/git/clone.py`** — `RepoCloneService` вынесен из `GitOperations`: жизненный цикл клонирования (`check_project`, `force_clone_repo`, `clone_repo`, `check_repo_url`); `GitOperations` делегирует через тонкие обёртки. Изолированные unit-тесты проверяют нормализацию URL, cwd при clone, shallow clone для platform и отсутствие `chdir` в `check_project`.
- **`dev_project/git/checkout.py`** — `CheckoutService` вынесен из `GitOperations`: оркестрация checkout (`checkout*`, `switch_to_branch`, low-level `_git_*`); `GitOperations` делегирует через тонкие обёртки. `apply_build_date` использует `CheckoutService.ensure_branch_exists`. Изолированные unit-тесты проверяют пропуск pull при явном commit, hard `switch_to_branch`, флаги `checkout_repository` и fetch для explicit commit.
- **`dev_project/git/build_date.py`** — `BuildDateResolver` вынесен из `GitOperations`: разрешение odoo build-date (`resolve_head_sha`, `resolve_commit_by_build_date`, `fetch_history_for_build_date`, `resolve_commit_with_fetch`, `apply_build_date`); `GitOperations` делегирует через тонкие обёртки. `apply_build_date` использует `CheckoutService.ensure_branch_exists`; `resolve_commit_with_fetch` сохраняет callback `link._fetch_history_for_build_date`. Добавлены `BuildDateResolverTests`; сценарии `test_git_build_date` без изменений.
- **`dev_project/git/link.py`** — `HandleOdooProjectLink` собирает `GitRunner`, `RepoCloneService`, `CheckoutService` и `BuildDateResolver` через `_wire_git_services()`; **`dev_project/git/operations.py` удалён**. Публичный API link без изменений; partial-link helpers в тестах вызывают `_wire_git_services()`. `HandleOdooProjectLinkGitServicesTests` заменяют `GitOperationsTests`.
- **`dev_project/config/manifests/`** — `UserSettingsReader` и `OdpmJsonReader` вынесены из бывшего фасада `ConfigLoader`; `odpm_json_writer.rewrite_odpm_json` записывает default manifest. `OdpmJsonReaderTests`, `UserSettingsReaderTests` и `OdpmJsonWriterTests` в `test_host_config`.
- **`dev_project/config/defaults/factory.py`** — `ConfigDefaultsFactory`: `get_developing_project_link`, `create_default_user_setting_json_content`, `create_default_odpm_json_content` (включая interactive prompt выбора версии Odoo); подключается через `ConfigBootstrapContext.defaults` и callbacks manifest readers. `ConfigDefaultsFactoryTests` в `test_host_config`; `test_noninteractive_init` патчит `defaults.factory`.
- **`dev_project/config/artifacts/deprecated.py`** — `DeprecatedConfigHandler`: миграция legacy `config.json` и сканирование deprecated placeholders в шаблонах; подключается через `ConfigBootstrapContext.deprecated` в bootstrap и layout. `DeprecatedConfigHandlerTests` в `test_host_config`; `test_template_upgrade` без изменений.
- **`dev_project/config/transforms/`** — `beautify_module_list` и `OdooBuildDateResolver` вынесены: нормализация списка модулей и разрешение build date; bootstrap подключает transforms через `ConfigBootstrapContext.build_date` и прямой импорт `beautify_module_list`. `ConfigTransformsTests` в `test_host_config`.
- **`dev_project/config/bootstrap_context.py`** — `ConfigBootstrapContext` заменяет `ConfigLoader` как composition root для manifests, artifacts, defaults и transforms; bootstrap и layout вызывают сервисы context напрямую; публичный `rewrite_odpm_json()` делегирует в `odpm_json_writer`. **`dev_project/config/loader.py` удалён**. `ConfigBootstrapContextWiringTests`, `BindDevelopingLinkTests`, `BindPlatformLinkTests`; bootstrap slice tests проверяют вызовы сервисов context; mocks `config._loader` убраны из тестов.
- **`dev_project/config/bootstrap_context.py` (C-6)** — `ConfigPaths`, `OdooConfBuilder` и `GitRepoCoordinator` подключены в `ConfigBootstrapContext`; `init_context` алиасит `config._paths` / `_odoo_conf` / `_git_repos` из context; `layout` использует `ctx.paths` и `ctx.odoo_conf`; `GitRepoCoordinator` получает injected `paths` и callback `bind_platform_link`. Тест host-services в `ConfigBootstrapContextWiringTests`; mocks `config._git_repos` убраны из `test_git_repos`.
- **`dev_project/project_env/services/platform_sources.py`** — `PlatformSourcesService` вынесен из `CreateProjectEnvironment`: `download_odoo_nightly_build`; `SystemChecker.check_file_system` подключает nightly download для server-сценария. Git clone platform для developer — в prepare `git.materialize` через `materialize_git_repos`. `PlatformSourcesServiceTests` в `test_project_env_links`.
- **`dev_project/project_env/services/platform_sources.py` (R-1)** — удалён неиспользуемый `download_odoo_repository` (clone с жёстким `ODOO_GIT_LINK`, без production callers); используйте `get_platform_sources` или `download_odoo_nightly_build`.
- **`dev_project/project_env/services/vscode_configurator.py`** — `VscodeConfigurator` вынесен из `ProjectTemplates`: граница VS Code; `RuntimeCoordinator.configure_vscode` вызывает сервис напрямую. `VscodeDebuggerMappingsTests` бьют сервис напрямую.
- **`dev_project/project_env/services/ci_image_build.py`** — `CiImageBuildService` вынесена оркестрация CI image build поверх `CiImageBuilder`; `RuntimeCoordinator.handle_build_image` вызывает сервис напрямую. `CiImageBuildServiceTests` в `test_project_env_modules`; pipeline tests патчат `CiImageBuildService`.
- **`dev_project/project_env/services/docker_base_image.py`** — `BaseImageService` вынесена оркестрация base image поверх `BaseImageBuilder`; `SystemChecker.check_docker` и `CiImageBuilder.build_ci_image` вызывают сервис напрямую. `BaseImageServiceTests` в `test_project_env_modules`; `test_phase2_infra` патчит `BaseImageService`.
- **`dev_project/project_env/environment.py` (E-5)** — `CreateProjectEnvironment` ужат до prepare wiring (`templates`, `compose_generator`, `links`, `mapped_folders`, attach system checker); runtime delegates удалены. Post-prepare runtime — в `RuntimeCoordinator` и `project_env.services`.
- **`dev_project/runtime_coordinator.py` (E-6)** — `RuntimeCoordinator` владеет post-prepare runtime (CI build, VS Code, compose up) через `run_after_prepare`; `OdpmPipeline` делегирует через тонкие обёртки. `RuntimeCoordinatorPolicyTests` и `RuntimeCoordinatorComposeTests` в `test_odpm_pipeline`; orchestration pipeline < 150 LOC.
- **P2 cleanup** — `RuntimeProjectServicesProtocol` удалён; phase-функции bootstrap перенесены в `config/bootstrap_phases.py` (`bootstrap.py` <100 LOC); server nightly через `PlatformSourcesService`; bullets E-1…E-4 в CHANGELOG исправлены.
- **`dev_project/check_system.py` (R-2)** — clone platform для developer выполняется только в prepare `git.materialize` (`materialize_git_repos`); init `check_file_system` лишь проверяет и логирует, если repo ещё не готов. Обновлены `test_phase2_infra` и `test_prepare_context`.
- **`dev_project/check_system.py` (R-3)** — nightly download platform в server-сценарии через `stdin_is_interactive` / `prompt_input`; в неинтерактивном режиме fail-fast с `NON_INTERACTIVE_SERVER_PLATFORM_MISSING` вместо блокировки на `input()`. Обновлены README EN+RU (server / non-interactive).
- **Политика CI (R-4)** — в README EN+RU добавлена **матрица CI**: `compose-smoke` (minimal fixture [`tests/fixtures/minimal_odpm_project/`](tests/fixtures/minimal_odpm_project/)) — gate на merge в PR; full `golden-path` — opt-in (nightly, `workflow_dispatch`, label `run-docker`, secret `ODPM_GOLDEN_PATH_PROJECT`). Комментарии для maintainers в `.github/workflows/ci-docker.yml`; обновлён `goals_ru.md` #5; синхронизированы `docs/smoke-4.0-checklist.md` и baseline post-audit plan. Задокументировано **634** passed.
- **`dev_project/host/cli/` (R-5)** — монолитный `parse_args.py` разбит на модули (`args_common`, `args_init`, `args_db`, `args_plan`, `args_compose`, `args_scaffold`); `parse_args.py` — тонкий facade (`build_arg_parser`, `parse_args`, `parse_cli_args`). Поведение CLI без изменений; порядок флагов в `--help` сохранён через явный порядок регистрации в `args_common`.

---

## [4.1.0] — 6 июня 2026 г.

Небольшой релиз, завершающий раскладку пакетов, начатую в 4.0: **root-shim модули удалены**. Используйте канонические пути под `dev_project.prepare`, `dev_project.plan`, `dev_project.compose` и `dev_project.host`.

### Критические изменения (несовместимость с 4.0 shims)

- **Удалены root-shim модули.** Следующие пути импорта больше не существуют; см. таблицу в README **Миграция импортов 4.0→4.1** и раздел Migration Guide ниже:
  - `dev_project.prepare_registry` → `dev_project.prepare`
  - `dev_project.plan_*` → `dev_project.plan.*`
  - `dev_project.compose_*`, `start_command` → `dev_project.compose.*`
  - `dev_project.host_*`, `host_cli/*` → `dev_project.host.*` / `dev_project.host.cli.*`
  - `dev_project.project_env.compose` → `dev_project.compose.generator.ComposeGenerator`
  - `dev_project.inside_docker_app.cli_params`, `parse_args` — удалены; checker использует `inside_docker_app.params`, host CLI — `dev_project.host.cli.*`
- **`DeprecationWarning` при import shim больше не выдаётся** — устаревшие импорты завершатся `ModuleNotFoundError`.

### Изменено

- **Production и тесты — только канонические импорты.** `ComposeGenerator` импортируется из `compose.generator`; обновление compose-шаблона — через `project_dir_manager.template_needs_upgrade`.
- **Имена CLI-флагов checker в контейнере** — модуль `dev_project.inside_docker_app.params` (без зависимости от host-пакетов).
- **590 тестов** в `unittest discover` (7 skipped — opt-in Docker integration); тесты deprecation и дублирующие shim smoke удалены.

### Migration Guide (4.0 → 4.1)

Если вы уже перевели импорты, когда shims в 4.0 выдавали `DeprecationWarning`, **дополнительных действий не требуется**.

1. **Замените оставшиеся root-shim импорты** в своих скриптах, CI и форках — по таблице в README **Миграция импортов 4.0→4.1**.
2. **Пример замены:**
   ```python
   # Было (shim 4.0 — удалён в 4.1)
   from dev_project.prepare_registry import make_prepare_context
   from dev_project.host_cli.args import OdpmCliArgs

   # Стало (4.1)
   from dev_project.prepare import make_prepare_context
   from dev_project.host.cli.args import OdpmCliArgs
   ```
3. **Перезапустите тесты расширений**; `@patch` должен указывать на канонический модуль (например `dev_project.compose.generator.template_needs_upgrade`).

---

## [4.0.0] — 6 июня 2026 г.

Четвёртая версия — это **крупное обновление архитектуры**, а не новый продукт с другой целью. Задача odpm остаётся прежней: по манифесту проекта воспроизвести рабочее окружение Odoo на любой машине. Изменился способ, которым это делается: вместо одного длинного сценария в `odpm.py` появился управляемый pipeline, типизированный контракт между хостом и контейнером, три режима использования, фиксация git-зависимостей и возможность установки через pip.

### Критические изменения (несовместимость с 3.x)

**Удалены устаревшие модули и пути импорта на стороне хоста.** Раньше конфигурация и окружение проекта жили в файлах `host_config.py`, `host_project_env.py`, `handle_odoo_project_git_link.py`, `host_start_string_builder.py`, а точкой входа контейнера был `inside_docker_app/main.py`. В версии 4.0 эти файлы удалены. Если у вас есть собственные скрипты, импортирующие их, перейдите на модули `dev_project.config`, `dev_project.git` и `dev_project.project_env`.

**Конфигурация контейнера передаётся только через файл.** Раньше настройки кодировались в base64 и вставлялись в длинную shell-команду в `docker-compose.yml`. Теперь odpm записывает JSON в `.odpm/runtime/config.json`, compose монтирует этот файл в контейнер, а переменная окружения `ODPM_CONFIG_PATH` указывает путь к нему. Переменная `ODPM_CONFIG_B64` больше не используется.

**Команда запуска Odoo в compose оформлена как exec-список**, а не как одна строка `bash -c '…'`. Стандартный путь — `python3 -m dev_project.inside_docker_app.run_odoo`. Это упрощает отладку и убирает хрупкие конструкции с вложенными кавычками.

**Удалён флаг `--pip-install`.** Устанавливать Python-пакеты «с хоста одной командой» больше нельзя: зависимости задаются в `odpm.json` (поле `requirements_txt`) и подтягиваются при старте контейнера вместе с транзитивными требованиями из графа зависимостей.

**Удалены `Config.config_dict` и связанные с ним устаревшие методы** на стороне хоста. Конфигурация собирается из типизированных «срезов» (настройки пользователя, настройки проекта, параметры Docker).

**Из шаблона docker-compose убраны старые плейсхолдеры:** `{START_STRING}`, `{MAPPED_VOLUMES}`, `{DEBUGGER_PORT_MAP}`, а также встроенный блок `healthcheck`. Если в каталоге проекта остались старые шаблоны, odpm при обнаружении устаревших маркеров переименует их в `deprecated_*` и предупредит в логе.

**Pre-commit в контейнере** запускается модулем `python3 -m dev_project.inside_docker_app.run_pre_commit`, а не оболочкой `/bin/bash -c`.

### Что добавлено

#### Оркестрация и структура кода

На хосте появился **`OdpmPipeline`** — единая точка, которая загружает конфигурацию, при необходимости показывает план действий, выполняет подготовку файлов проекта и запускает compose. Сам этап подготовки (git, шаблоны, runtime-конфиг, генерация compose) вынесен в **`ProjectMaterializer`**, чтобы его можно было отделить от запуска контейнеров и от режима «только показать, что будет сделано».

Класс **`Config`** перестал быть монолитом на сотни строк: загрузка разбита на фазы bootstrap, настройки пользователя и проекта хранятся в отдельных typed-состояниях. Для read-only доступа к путям и политике добавлен **`HostProjectContext`**, для параметров compose во время выполнения — **`HostRuntimeState`**.

Host больше **не меняет глобальную рабочую директорию процесса** (`os.chdir`): все subprocess вызываются с явным `cwd=`. Ошибки оформлены иерархией исключений вместо разрозненных `sys.exit`.

#### Контракт «хост — контейнер»

Введён **`ContainerConfig` версии 1** — типизированное описание того, что контейнеру нужно знать при старте, с JSON-схемой и проверкой средствами стандартной библиотеки Python. Старый формат без `schema_version` по-прежнему читается (миграция с legacy v0).

Команда Odoo в compose собирается через **`ComposeServiceBuilder`** и **`StartCommand`** — структурированный список аргументов, а не склеенная shell-строка.

#### Три сценария использования

Параметр **`ODPM_SCENARIO`** в файле `.env` выбирает режим работы; поведение задаёт **`ScenarioPolicy`**:

- **`developer`** — локальная разработка: отладчик debugpy, режим `--dev` Odoo из `user_settings.json`, виртуальное окружение пересоздаётся при изменении lock (режим `fresh`).
- **`server`** — запуск как сервис: без debugpy, PostgreSQL на хосте слушает только localhost; параметр `dev_mode` игнорируется с предупреждением.
- **`ci`** — сборка и запуск на CI: исходники и venv «запекаются» в образ, bind-mount исходников Odoo не используется, доступна команда **`odpm --build-image`**.

Явно разделены **`HOST_USER`** (пользователь на машине, где крутится Docker) и **`CONTAINER_USER`** (пользователь внутри контейнера Odoo).

Для режима разработки с флагами `reload` или `all` в `dev_mode` odpm **автоматически добавляет пакет `inotify`** в требования Python, чтобы работала перезагрузка кода.

#### Git-зависимости и воспроизводимость

Появился файл **`.odpm/deps.lock.json`**: в нём фиксируются коммиты git-репозиториев (платформа Odoo, разрабатываемый проект, полный граф зависимостей). Команда **`odpm --update-lock`** пересчитывает lock и сохраняет его; **`odpm --no-git-update`**, наоборот, пропускает обновление git и полезна в офлайн-сценариях.

Механизм **`use_oca_dependencies`** (по умолчанию выключен) расширен: читаются `oca_dependencies.txt` и вложенные `odpm.json` в корнях зависимостей, строится транзитивный граф; в сценарии CI несовместимость версий Odoo/Python приводит к ошибке, в developer — к предупреждению.

#### Установка и удобство разработчика

odpm можно **установить через pip** — в PATH появится команда `odpm`. По-прежнему поддерживается «legacy»-режим: скопировать `odpm.py` и каталог `dev_project` из репозитория.

**План (dry-run):** команда **`odpm plan`** показывает шаги prepare и runtime, которые выполнились бы при обычном запуске, без git materialize, записи runtime-конфига и корневого compose и без `docker compose up`. Устаревший alias **`--plan`** сохранён. У каждого шага — исход (`run`, `update`, `noop`, `skip`) и причина; для `compose.up` предсказывается, понадобится ли `--force-recreate` (probe локального stack, отключается `--plan-no-docker`). Флаги: `--plan-show-diff` (unified diff для runtime config, compose, dockerignore), `--plan-format json` (вывод в stdout для скриптов), `--plan-strict` (ненулевой код выхода, если обязательные шаги изменят состояние). Таблица идёт в лог, JSON — в stdout. В режиме plan шаблоны в `.odpm/` не обновляются (обычный запуск `odpm` по-прежнему их синхронизирует). Без `--plan-no-docker` odpm может проверить локальный compose stack для предсказания `compose.up`.

Добавлен **режим без интерактивного ввода** для CI и скриптов: если stdin не привязан к терминалу, odpm не задаёт вопросов через `input()`.

Шаблон **`.dockerignore`** хранится в `.odpm/dockerignore` и при каждом запуске копируется в корень проекта; править нужно шаблон, а не сгенерированный файл в корне.

#### Декомпозиция модулей

- **Хост:** пакет `git/` (`GitRepoCoordinator`, операции, deps lock), пакет `project_env/` (шаблоны, compose, CI-образ, ссылки, volume mapper, symlink manager).
- **Контейнер:** пакет `odoo_checker/` (БД, admin, i18n, SQL), `run_odoo`, `run_pre_commit`, library-only `container_bootstrap`.
- **Сборка CI-образа** — `Dockerfile.ci`, baked runtime config в build context, `odpm --build-image` (только сценарий ci).

#### Качество и проверки

- **597 тестов** в `unittest discover` (по умолчанию 7 opt-in Docker integration tests пропускаются).
- **Plan-safe setup** — `odpm plan` загружает конфигурацию без обновления шаблонов в `.odpm/`; обычный запуск по-прежнему синхронизирует шаблоны проекта при старте.
- **Восстановление устаревшего odoo.conf** — `odpm --skip-start` пересоздаёт `odoo.conf`, если в нём нет настроек подключения к БД Docker (например после апгрейда с layout без `db_host`).
- **Пакет `dev_project/prepare/`** — реестр prepare-фазы вынесен из монолитного `prepare_registry.py`; shim сохраняет существующие импорты и patch-пути в тестах.
- **Пакет `dev_project/host/`** — host context, runtime, user `.env` и CLI (`host/cli/`); legacy-пути `host_cli/` и `host_*.py` сохранены как shims.
- **Пакет `dev_project/compose/`** — compose service builder, start command, YAML render, generator и runtime helpers; legacy-пути `compose_*.py`, `start_command.py` и `project_env.compose` сохранены как shims.
- **Пакет `dev_project/plan/`** — plan core, planner, CLI, formatters, diffs и compose/runtime preview; legacy-пути `plan_*.py` сохранены как shims.
- **`OdpmCliArgs` typed CLI** — frozen dataclass с bridge `from_namespace` и `parse_cli_args()`; host pipeline (`OdpmPipeline`, prepare/plan/config) использует `OdpmCliArgs` целиком; `Namespace` остаётся только в `parse_args()` и container dispatch shim.
- **Нативный subcommand `odpm plan`** — общий argparse parent parser; `odpm plan --skip-start` парсится без rewrite argv; глобальный `--plan` остаётся deprecated alias с предупреждением.
- **GitHub Actions CI** (`.github/workflows/ci.yml`) — unit-suite при каждом push/PR в `4.0-beta` и `main` (Python 3.10 и 3.12); повторный запуск вручную — через **workflow_dispatch**.
- **GitHub Actions Docker CI** (`.github/workflows/ci-docker.yml`) — compose smoke при каждом push/PR (`odpm --skip-start` на minimal fixture + `docker compose config`); full golden-path — nightly, **workflow_dispatch** или label PR `run-docker`.
- **Opt-in Docker integration tests:** сборка CI-образа, golden-path compose + HTTP 200 (`ODPM_RUN_DOCKER_INTEGRATION=1`).
- **Скрипты:** `scripts/verify_ci_scenario.sh`, `scripts/run_compose_smoke_test.sh`, `scripts/run_golden_path_test.sh`, `scripts/verify_dev_mode_flags.sh`, `scripts/verify_dev_mode_autoreload.sh`.

### Что изменилось по сравнению с 3.x

- Runtime-конфигурация записывается в `.odpm/runtime/config.json` на хосте (developer/server) или запекается в CI-образ.
- Git materialization и обработка build-date платформы сосредоточены в **`GitRepoCoordinator`**.
- Разрешение зависимостей — один проход BFS через `DependencyMaterializer` и `dependency_resolver.py`.
- Compose stack может стартовать **без `--force-recreate`**, если текущий stack уже здоров (`compose/runtime`).
- Устаревшие артефакты проекта (`config.json`, старые маркеры compose/dockerfile) переименовываются в `deprecated_*` с предупреждением.
- Единое host-логирование в `dev_project.logging` (container re-export shim временно сохранён).
- **Освобождение портов в developer отделено от `check_system`.** Prepare-шаг `docker.ports.release` всегда выполняется в developer-сценарии перед compose и останавливает контейнеры на портах odoo/debugger/postgres/gevent; `docker.engine.check` (beginner-проверки git/docker) остаётся за флагом `check_system`.
- **Production-импорты переведены на канонические пути.** `ProjectMaterializer`, `OdpmPlanner`, `prepare/execute` и `plan/runtime_preview` используют `dev_project.prepare`, `dev_project.git.deps_lock_manager` и `dev_project.plan.compose_preview` вместо root-shim `prepare_registry`, `plan_compose_preview` и `plan_runtime_preview`.
- **Unit-тесты патчат канонические модули.** `@patch` переведены с root-shim (`prepare_registry`, `compose_runtime`, `plan_format`, …) на `dev_project.compose.*`, `dev_project.plan.*`, `dev_project.prepare.*` и `dev_project.config.payload`; связанные call site в compose/plan/prepare больше не ходят через self-shim.
- **Preview-слой plan унифицирован.** `preview_runtime_config_text` и `prepare_runtime_config_for_compose_preview` в `plan/compose_preview.py`; `plan/preview.py` re-export compose/runtime preview helpers. `prepare/steps_compose.py` и `prepare/runtime.py` импортируют plan/compose напрямую, без `prepare_registry` в `prepare/`.
- **`SystemCheckPolicy` централизует gating проверок.** Модуль `dev_project/system_check_policy.py` задаёт `beginner_git`, `beginner_docker`, `developer_port_release`, `compose_validate` и `file_system_on_init`; `SystemChecker`, prepare docker steps и pipeline setup читают policy вместо разрозненных проверок `check_system`/scenario.
- **Root-shim импорты выдают `DeprecationWarning`.** Backward-compatible модули (`prepare_registry`, `plan_*`, `compose_*`, `host_*`, `host_cli/*`, `inside_docker_app/cli_params`, `inside_docker_app/parse_args`, `project_env.compose`) предупреждают при import с указанием канонического пути; см. README **Миграция импортов 4.0→4.1**. Shims будут удалены в 4.1.0.
- **`PrepareContext` injectит prepare-сервисы.** `ProjectTemplates`, `ComposeGenerator` и `ProjectLinks` создаются в `make_prepare_context` из `CreateProjectEnvironment` (или для plan-only/mock env).
- **Prepare steps вызывают inject-сервисы напрямую.** Template, compose и project steps выполняются через `ctx.templates`, `ctx.compose_generator` и `ctx.links`; compose preview читает volume map и generator из того же context. Git checkout через `ctx.links`.
- **`CreateProjectEnvironment` только runtime; protocols split.** Prepare-операции на `ProjectTemplates`, `ComposeGenerator` и `ProjectLinks`; `CreateProjectEnvironment` реализует только `RuntimeProjectServicesProtocol` (`PrepareProjectServicesProtocol` описывает prepare surface). Prepare-делегаты удалены из `CreateProjectEnvironment`.

  > **Примечание (4.2):** `RuntimeProjectServicesProtocol` удалён; runtime — в `project_env.services` + `RuntimeCoordinator`. `PrepareProjectServicesProtocol` остаётся в `dev_project.protocols`. См. [Unreleased] P2 cleanup.

### Исправлено

- **`check_system: false` больше не пропускает освобождение портов.** Регрессия после plan-safe docker check: занятые порты (например PostgreSQL на 5432) приводили к ошибке bind при переключении между odpm-проектами с отключёнными проверками.
- **Ошибки subprocess больше не игнорируются на обязательных командах.** Добавлены `SubprocessError` и `run_or_raise()`; system checks и probe base image завершаются явной ошибкой; сбой `docker container ls` даёт `SystemCheckError` при освобождении портов.

### Что удалено

Флаг `--pip-install`, передача конфигурации через base64, удалённые shims (см. выше), healthcheck в шаблоне compose по умолчанию. Из документированной модели 4.0 убран отдельный глобальный путь **`ODOO_SRC_DIR`** в `.env` — платформа Odoo управляется через каталог проектов `ODOO_PROJECTS_DIR`.

### Как перейти с версии 3.x на 4.0

1. **Установите odpm 4.0.** Нужен Python 3.10 или новее; на дистрибутивах с PEP 668 (защита системного Python) удобнее venv или `pipx`. Предпочтительный способ:
   ```bash
   pip install /путь/к/клону/odpm
   # или editable для разработки самого odpm:
   pip install -e /путь/к/клону/odpm
   odpm --version
   ```
   Альтернатива — скопировать `odpm.py` и каталог `dev_project` с ветки `4.0-beta`.

2. **Перегенерируйте файлы проекта**, находясь в каталоге окружения odpm:
   ```bash
   odpm --skip-start
   ```
   Так обновятся Dockerfile, compose, runtime-конфиг и связанные шаблоны без немедленного старта контейнеров.

3. **Откройте сгенерированный `docker-compose.yml`** и убедитесь, что команда Odoo — exec-список с `run_odoo`, задан `ODPM_CONFIG_PATH=/run/odpm/config.json` и read-only mount файла `.odpm/runtime/config.json`, нет старых плейсхолдеров вроде `{START_STRING}`.

4. **Проверьте свои скрипты** на импорты удалённых модулей.

5. **Перенесите Python-зависимости** в `odpm.json` → `requirements_txt`. Флаг `--pip-install` больше не работает.

6. **Для CI:** установите `ODPM_SCENARIO=ci`, выполните `odpm --build-image`, при изменении git-зависимостей — `odpm --update-lock` и закоммитьте `.odpm/deps.lock.json`.

7. **Для команды с фиксированными версиями git-репозиториев** один раз выполните `--update-lock` и добавьте lock-файл в систему контроля версий.

Английская версия: [CHANGELOG.md](CHANGELOG.md).

---

## [3.0.0] — 11 января 2023 г.

Запись ниже составлена **задним числом** по ветке `3.0` и истории git: отдельный CHANGELOG для третьей версии раньше не вёлся. Линия 3.x развивалась до весны 2026 года; здесь описано состояние, которое пользователи 3.x фактически получали перед переходом на 4.0.

### Что такое odpm 3.0

Третья версия — это инструмент для **локальной разработки на Odoo в Docker**. Пользователь создаёт каталог окружения, указывает ссылку на репозиторий разрабатываемого проекта (или локальный путь), и odpm автоматически готовит машину: клонирует Odoo и зависимости, собирает образ, генерирует `docker-compose.yml`, настраивает отладчик в VS Code и запускает Odoo. Главная идея уже была заложена: **достаточно файла `odpm.json` в репозитории проекта**, чтобы на другой машине воспроизвести то же окружение.

### Как это было устроено внутри

Архитектура 3.0 — **монолитная и процедурная**. Весь сценарий подготовки шёл из `odpm.py` подряд: создание конфигурации, маппинг томов, генерация Dockerfile и compose, checkout зависимостей, настройка VS Code — затем смена рабочей директории процесса и вызов `docker compose up` через `os.system`, всегда с `--force-recreate`.

Конфигурация для контейнера сериализовалась в JSON, кодировалась в base64 и **вставлялась в одну длинную shell-команду** в шаблоне compose (`StartStringBuilder`). Внутри контейнера точка входа декодировала base64 и передавала словарь в проверку виртуального окружения и в монолитный модуль `check_odoo.py` (работа с БД, backup, admin, SQL, переводы).

В репозитории odpm было **29 модулей Python** и **не было автоматических тестов**. Два сценария в `.env`: **`developer`** (по умолчанию) и **`server`** (ограничение доступа к PostgreSQL и отключение отладчика на уровне compose). Отдельного сценария **CI** с «запечённым» окружением в образе не существовало.

### Что умело odpm 3.0 (функции)

**Инициализация проекта:** флаг `--init` с git-URL, SSH или `file://`; `--branch` для ветки разрабатываемого репозитория; параметры создания `odpm.json` (версия Odoo, ссылка на форк платформы, Python, дистрибутив Linux, PostgreSQL, список pip-пакетов).

**Docker и окружение:** автогенерация Dockerfile под Debian (и экспериментально Ubuntu); compose с PostgreSQL и bind-томом для данных; интерактивный опрос при первом создании `.env` (порты, каталог бэкапов, каталог клонов git, SSH-ключ); проверки наличия git, Docker, compose, свободного места и занятых портов.

**Git и зависимости:** клонирование и обновление платформы Odoo, developing-проекта и списка `dependencies` из `odpm.json`; checkout платформы на дату nightly-сборки (`--odoo-build-date`); экспериментальная подгрузка репозиториев из `oca_dependencies.txt`; экспериментальные симлинки модулей в `odoo/addons` для IDE; сканирование Python-зависимостей из манифестов модулей Odoo.

**Работа с Odoo из командной строки:** создание и обновление БД (`-d`, `-i`, `-u`), тесты модулей (`-t`, `--screencasts`), проброс аргументов odoo-bin (`--odoo-bin`), subcommand `scaffold` для генерации модуля; резервное копирование и восстановление БД, список баз, смена пароля администратора, выполнение SQL из настроек, экспорт po/pot, обновление переводов, запуск pre-commit; ожидание готовности PostgreSQL; поддержка Odoo вплоть до **19.0**.

**Python:** установка пакетов с хоста через **`--pip-install`**; виртуальное окружение в контейнере обновлялось при старте.

**IDE и документация:** генерация конфигурации VS Code для подключения debugpy; README на русском и английском; gettext-переводы интерфейса odpm.

### Ограничения 3.0 (устранены в 4.0)

Не было lock-файла git-зависимостей, режима «не трогать git», команды «показать план без изменений», pip-пакета, типизированного контракта host↔container, сценария CI с образом «всё внутри», автоматического набора регрессионных тестов в репозитории odpm. Передача настроек через base64 и shell в compose затрудняла отладку и сопровождение — это и стало главным мотивом архитектурного переписывания в версии 4.0.

---

## [2.0.0] и ранее

Ранние этапы (ветки `2.0`, `2.5`) описаны в истории git: переход от `config.json` к `odpm.json`, появление Docker-based workflow и первых сценариев автоматизации окружения Odoo.
