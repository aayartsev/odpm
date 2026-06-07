# История изменений

Здесь описаны значимые изменения **odpm** (Odoo Developer Project Manager) — инструмента, который по описанию проекта в файле `odpm.json` разворачивает окружение для разработки на платформе Odoo: клонирует исходники, собирает Docker-образ, поднимает PostgreSQL и Odoo, настраивает отладчик в VS Code.

Формат ориентирован на [Keep a Changelog](https://keepachangelog.com/ru/1.1.0/), но текст написан развёрнуто — для тех, кто не следил за внутренней историей репозитория.

---

## [Unreleased]

### Изменено

- **`dev_project/git/runner.py`** — `GitRunner` вынесен из `GitOperations`: сборка git-argv (в т.ч. SSH) и вызов `run_checked`; `GitOperations` делегирует через `_build_git_cmd` / `_run_git`. Unit-тесты проверяют argv, cwd по умолчанию и явный cwd.
- **`dev_project/git/clone.py`** — `RepoCloneService` вынесен из `GitOperations`: жизненный цикл клонирования (`check_project`, `force_clone_repo`, `clone_repo`, `check_repo_url`); `GitOperations` делегирует через тонкие обёртки. Изолированные unit-тесты проверяют нормализацию URL, cwd при clone, shallow clone для platform и отсутствие `chdir` в `check_project`.
- **`dev_project/git/checkout.py`** — `CheckoutService` вынесен из `GitOperations`: оркестрация checkout (`checkout*`, `switch_to_branch`, low-level `_git_*`); `GitOperations` делегирует через тонкие обёртки. `apply_build_date` использует `CheckoutService.ensure_branch_exists`. Изолированные unit-тесты проверяют пропуск pull при явном commit, hard `switch_to_branch`, флаги `checkout_repository` и fetch для explicit commit.
- **`dev_project/git/build_date.py`** — `BuildDateResolver` вынесен из `GitOperations`: разрешение odoo build-date (`resolve_head_sha`, `resolve_commit_by_build_date`, `fetch_history_for_build_date`, `resolve_commit_with_fetch`, `apply_build_date`); `GitOperations` делегирует через тонкие обёртки. `apply_build_date` использует `CheckoutService.ensure_branch_exists`; `resolve_commit_with_fetch` сохраняет callback `link._fetch_history_for_build_date`. Добавлены `BuildDateResolverTests`; сценарии `test_git_build_date` без изменений.
- **`dev_project/git/link.py`** — `HandleOdooProjectLink` собирает `GitRunner`, `RepoCloneService`, `CheckoutService` и `BuildDateResolver` через `_wire_git_services()`; **`dev_project/git/operations.py` удалён**. Публичный API link без изменений; partial-link helpers в тестах вызывают `_wire_git_services()`. `HandleOdooProjectLinkGitServicesTests` заменяют `GitOperationsTests`.
- **`dev_project/config/manifests/`** — `UserSettingsReader` и `OdpmJsonReader` вынесены из `ConfigLoader`: пути manifest-файлов и загрузка JSON; `ConfigLoader` делегирует через тонкие обёртки. `rewrite_odpm_json` остаётся в loader до C-5. `OdpmJsonReaderTests`, `UserSettingsReaderTests` и тесты делегирования loader в `test_host_config`.
- **`dev_project/config/defaults/factory.py`** — `ConfigDefaultsFactory` вынесен из `ConfigLoader`: `get_developing_project_link`, `create_default_user_setting_json_content`, `create_default_odpm_json_content` (включая interactive prompt выбора версии Odoo); loader и manifest readers подключаются через `_defaults`. `ConfigDefaultsFactoryTests` в `test_host_config`; `test_noninteractive_init` патчит `defaults.factory`.
- **`dev_project/config/artifacts/deprecated.py`** — `DeprecatedConfigHandler` вынесен из `ConfigLoader`: миграция legacy `config.json` и сканирование deprecated placeholders в шаблонах; `ConfigLoader` делегирует через тонкие обёртки. `DeprecatedConfigHandlerTests` и тесты делегирования loader в `test_host_config`; `test_template_upgrade` без изменений.
- **`dev_project/config/transforms/`** — `beautify_module_list` и `OdooBuildDateResolver` вынесены из `ConfigLoader`: нормализация списка модулей и разрешение build date; bootstrap подключает transforms напрямую (`beautify_module_list`, `config._build_date`); loader сохраняет тонкие обёртки делегирования. `ConfigTransformsTests`, `ConfigLoaderRewriteOdpmJsonTests` и тесты делегирования loader в `test_host_config`; mocks transform-методов на `config._loader` убраны из bootstrap slice tests.

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

### Исправлено

- **`check_system: false` больше не пропускает освобождение портов.** Регрессия после plan-safe docker check: занятые порты (например PostgreSQL на 5432) приводили к ошибке bind при переключении между odpm-проектами с отключёнными проверками.
- **Ошибки subprocess больше не игнорируются на обязательных командах.** Добавлены `SubprocessError` и `run_or_raise()`; system checks и probe base image завершаются явной ошибкой; сбой `docker container ls` даёт `SystemCheckError` при освобождении портов.

### Что удалено

Флаг `--pip-install`, передача конфигурации через base64, удалённые shims (см. выше), healthcheck в шаблоне compose по умолчанию. Из документированной модели 4.0 убран отдельный глобальный путь **`ODOO_SRC_DIR`** в `.env` — платформа Odoo управляется через каталог проектов `ODOO_PROJECTS_DIR`.

### Как перейти с версии 3.x на 4.0

1. **Установите odpm 4.0.** Нужен Python 3.10 или новее; на дистрибутивах с PEP 668 (защита системного Python) удобнее venv или `pipx`. Предпочтительный способ:
   ```bash
   pip install /путь/к/клону/odoo_dev_project
   # или editable для разработки самого odpm:
   pip install -e /путь/к/клону/odoo_dev_project
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
