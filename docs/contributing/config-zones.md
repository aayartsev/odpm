# Зоны Config

Карта того, **из чего собран** хостовый снимок ([`AssembledProject`](../../dev_project/config/config.py), внутренний сборщик; публичного `Config` нет) и **куда снаружи смотреть**, вместо обращения ко всему объекту сразу.

Поведение команд `odpm` эта карта не меняет. Контракт потребления: [ADR-003](adr-003-host-ports-vs-config.md), [ADR-030](adr-030-config-as-assembler.md). Гейт: `tests/test_no_public_config.py`.

## Роль

При `OdpmPipeline.setup` объект `AssembledProject` **собирает** снимок проекта (настройки, манифест, политика, пути). Снаружи оркестратора публичного снимка нет: только порты сеанса (`PipelinePorts`) и ручка `BootstrapHandle`. Дальше:

| Нужно | Брать |
|-------|--------|
| Пути, политика, срезы настроек (чтение) | [`HostProjectContext`](../../dev_project/host/context.py) |
| Оценка плана / шагов подготовки | порты (`PlanPorts` / `PrepareContext.host_ctx`) |
| Выполнение шагов (git, lock, env, секреты, шаблон compose) | [`BootstrapHandle`](../../dev_project/host/ports.py) и хелперы [`PrepareContext`](../../dev_project/prepare/types.py): `git_repos`, `env_resolver`, `pd_manager`, `secrets_session`, `clear_runtime_config_preview_cache`, … |
| Оценка IDE после prepare | [`RuntimePorts`](../../dev_project/host/ports.py): `debug_profile_needs_update`, `vscode_settings_up_to_date`, `pycharm_run_config_*` |
| Превью compose / runtime / IDE в плане | [`ComposePreviewPort`](../../dev_project/prepare/compose_preview_port.py) и модули `plan/*_preview.py`: ручка / `host_ctx` (не голый `Config`); кэш runtime-превью на ручке (`clear_runtime_config_preview_cache`); запись runtime JSON снаружи `config/` — через accessors ручки |
| Генератор `odoo.conf` | `bootstrap.odoo_conf` (на handle уже есть; прямые вызовы / следующие шаги — сюда, не в `config._odoo_conf`) |
| Окружение проекта (`CreateProjectEnvironment`) | передавать `BootstrapHandle`; сервисы без публичного `.config`. Пути и срезы — через `env.host_ctx` или accessors ручки (публичного `env.bootstrap.config` нет) |
| Host API БД / module-diff / manifest / system check | БД и module-diff — от ручки; `odpm manifest` — `ports.bootstrap` / `host_ctx`; проверка системы — `SystemCheckPolicy.from_bootstrap` |
| Сборка портов / host_ctx | [`ports_from_assembled`](../../dev_project/config/assembly.py) / `host_context_from_assembled` в `config/` (не `ports_from_config` / `from_config` на `host/`) |
| Шаги `prepare/steps_*.py` и `prepare/runtime.py` | только handle / `RuntimePorts` / хелперы; сырой `bootstrap.config` / `ctx.config` запрещён |
| Сырой снимок сборщика | только внутри `dev_project/config/` и как приватное `_assembled` у ручки; снаружи — accessors |

Новые шаги и фичи **не** добавляют плоские свойства на сборщик «для удобства».
Автоматических свойств `bind_slice_properties` больше нет: поля читаются явно
через `user_settings`, `project_settings`, `docker_layout`
и `addon_layout` на сборщике / через accessors ручки.

Шаги в `dev_project/prepare/steps_*.py` и оценка IDE в `prepare/runtime.py` не читают сырой снимок. Нужное берут с `BootstrapHandle` / `RuntimePorts` и с хелперов `PrepareContext`. Запрет строк `bootstrap.config` и `ctx.config` в этих файлах проверяет `tests/test_prepare_config_coupling.py`. Превью compose в плане идёт через `ComposePreviewPort.run_with_mutable_snapshot`. Алиаса `PrepareContext.config` **нет**. У ручки нет публичного `.config` (кампания G): снимок — `_assembled`, снаружи только accessors. Фасады git/symlink/nested/odoo.conf-docker — только на ручке (кампания H); у `AssembledProject` их нет.

## Зоны внутри сборки

| Зона | Где в коде | Смысл |
|------|------------|--------|
| Каркас сеанса | `project_dir`, `program_dir`, `arguments`, `user_env`, `pd_manager` | Где проект и с какими флагами вызвали |
| Настройки пользователя | `UserSettingsState` | `user_settings.json` |
| Манифест проекта | `ProjectSettingsState`, сырой `odpm.json` | Версии, зависимости, платформа |
| Bootstrap git / манифест | `BootstrapState` | Ссылки developing/platform, `manifest_view` |
| Политика сценария | `ScenarioPolicy` (`assembled.policy` / `host_ctx.policy`) | Правила `developer` / `server` / `ci` |
| Docker и аддоны | `DockerLayoutState`, `AddonLayoutState` | Шаблоны, тома, каталоги модулей |
| Env и секреты | `EnvResolver`, сессия секретов | Подстановки `${…}` / `${@secret:…}` |
| Исполнители на границе | `GitRepoCoordinator`, `OdooConfBuilder` (через ручку) | Клон/ссылки, генерация odoo.conf |
| Живое состояние запуска | `HostRuntimeState` (`assembled.runtime`, `bootstrap.runtime`) | Команда compose и возможности Docker — состояние **сеанса**, не описание проекта |

Сборка по фазам: [`bootstrap.py`](../../dev_project/config/bootstrap.py).

## Отличие от соседних карт

- [Зоны подготовки](prepare-zones.md) — **шаги** `prepare` / `plan` (git, карта папок, compose).
- [Движок запуска](runtime-backend.md) — **как поднять стек** после prepare.
- Эта страница — **из чего состоит снимок `AssembledProject`** и через какие порты к нему ходить.

## Связанные документы

- [ADR-003](adr-003-host-ports-vs-config.md) — порты vs сборщик
- [ADR-030](adr-030-config-as-assembler.md) — `AssembledProject` как сборщик
- [cli-architecture.md](cli-architecture.md) — маршрутизация команд
