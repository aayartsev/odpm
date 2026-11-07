# Зоны Config

Карта того, **из чего собран** хостовый [`Config`](../../dev_project/config/config.py) и **куда снаружи смотреть**, вместо обращения ко всему объекту сразу.

Поведение команд `odpm` эта карта не меняет. Контракт потребления: [ADR-003](adr-003-host-ports-vs-config.md), [ADR-030](adr-030-config-as-assembler.md).

## Роль

При `OdpmPipeline.setup` объект `Config` **собирает** снимок проекта (настройки, манифест, политика, пути). Снаружи оркестратора публичного снимка нет: только порты сеанса (`PipelinePorts`) и ручка `BootstrapHandle`. Дальше:

| Нужно | Брать |
|-------|--------|
| Пути, политика, срезы настроек (чтение) | [`HostProjectContext`](../../dev_project/host/context.py) |
| Оценка плана / шагов подготовки | порты (`PlanPorts` / `PrepareContext.host_ctx`) |
| Выполнение шагов (git, lock, env, секреты, шаблон compose) | [`BootstrapHandle`](../../dev_project/host/ports.py) и хелперы [`PrepareContext`](../../dev_project/prepare/types.py): `git_repos`, `env_resolver`, `pd_manager`, `secrets_session`, `clear_runtime_config_preview_cache`, … |
| Оценка IDE после prepare | [`RuntimePorts`](../../dev_project/host/ports.py): `debug_profile_needs_update`, `vscode_settings_up_to_date`, `pycharm_run_config_*` |
| Превью compose в плане | [`ComposePreviewPort`](../../dev_project/prepare/compose_preview_port.py) (`run_with_mutable_snapshot`, без выдачи сырого снимка наружу) |
| Генератор `odoo.conf` | `bootstrap.odoo_conf` (на handle уже есть; прямые вызовы / следующие шаги — сюда, не в `config._odoo_conf`) |
| Окружение проекта (`CreateProjectEnvironment`) | передавать `BootstrapHandle`; сервисы без публичного `.config`. `DependencyMaterializer` — от ручки. Links / VolumeMapper / CI bake: пути и срезы настроек через `env.host_ctx`, accessors ручки (`env_resolver`, `compute_venv_lock_hash`); git-объекты, мутации и API на Config — `env.bootstrap.config` внутри методов |
| Host API БД / module-diff | `collect_database_status`, `ensure_app_role`, adopt / blocking-drift, `detect_database_drift_for_handle`, `compute_module_diff_for_handle` — от `BootstrapHandle` (не голый `Config`) |
| Шаги `prepare/steps_*.py` и `prepare/runtime.py` | только handle / `RuntimePorts` / хелперы; сырой `bootstrap.config` / `ctx.config` запрещён |
| Сырой `bootstrap.config` | хвосты внутри хелперов/API с `Config`, drift, сборка compose-сервиса — пока нет узкого accessor |

Новые шаги и фичи **не** добавляют плоские свойства на `Config` «для удобства».
Автоматических свойств `bind_slice_properties` больше нет: поля читаются явно
через `config.user_settings`, `config.project_settings`, `config.docker_layout`
и `config.addon_layout`.

Шаги в `dev_project/prepare/steps_*.py` и оценка IDE в `prepare/runtime.py` не читают сырой снимок. Нужное берут с `BootstrapHandle` / `RuntimePorts` и с хелперов `PrepareContext`. Запрет строк `bootstrap.config` и `ctx.config` в этих файлах проверяет `tests/test_prepare_config_coupling.py`. Превью compose в плане идёт через `ComposePreviewPort.run_with_mutable_snapshot`. Внутри хелпера вызов API, который ещё принимает `Config`, допустим. Алиаса `PrepareContext.config` **нет** (срез C): сырой снимок — только через `ports.bootstrap.config` внутри хелперов/API.

## Зоны внутри сборки

| Зона | Где в коде | Смысл |
|------|------------|--------|
| Каркас сеанса | `project_dir`, `program_dir`, `arguments`, `user_env`, `pd_manager` | Где проект и с какими флагами вызвали |
| Настройки пользователя | `UserSettingsState` | `user_settings.json` |
| Манифест проекта | `ProjectSettingsState`, сырой `odpm.json` | Версии, зависимости, платформа |
| Bootstrap git / манифест | `BootstrapState` | Ссылки developing/platform, `manifest_view` |
| Политика сценария | `ScenarioPolicy` (`config.policy`) | Правила `developer` / `server` / `ci` |
| Docker и аддоны | `DockerLayoutState`, `AddonLayoutState` | Шаблоны, тома, каталоги модулей |
| Env и секреты | `EnvResolver`, сессия секретов | Подстановки `${…}` / `${@secret:…}` |
| Исполнители на границе | `GitRepoCoordinator`, `OdooConfBuilder` | Клон/ссылки, генерация odoo.conf |
| Живое состояние запуска | `HostRuntimeState` (`config.runtime`, `bootstrap.runtime`) | Команда compose и возможности Docker — состояние **сеанса**, не описание проекта |

Сборка по фазам: [`bootstrap.py`](../../dev_project/config/bootstrap.py).

## Отличие от соседних карт

- [Зоны подготовки](prepare-zones.md) — **шаги** `prepare` / `plan` (git, карта папок, compose).
- [Движок запуска](runtime-backend.md) — **как поднять стек** после prepare.
- Эта страница — **из чего состоит снимок Config** и через какие порты к нему ходить.

## Связанные документы

- [ADR-003](adr-003-host-ports-vs-config.md) — порты vs Config
- [ADR-030](adr-030-config-as-assembler.md) — Config как сборщик
- [cli-architecture.md](cli-architecture.md) — маршрутизация команд
