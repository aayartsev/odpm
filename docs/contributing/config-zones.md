# Зоны Config

Карта того, **из чего собран** хостовый [`Config`](../../dev_project/config/config.py) и **куда снаружи смотреть**, вместо обращения ко всему объекту сразу.

Поведение команд `odpm` эта карта не меняет. Контракт потребления: [ADR-003](adr-003-host-ports-vs-config.md), [ADR-030](adr-030-config-as-assembler.md).

## Роль

При `OdpmPipeline.setup` объект `Config` **собирает** снимок проекта (настройки, манифест, политика, пути). Дальше:

| Нужно | Брать |
|-------|--------|
| Пути, политика, срезы настроек (чтение) | [`HostProjectContext`](../../dev_project/host/context.py) |
| Оценка плана / шагов подготовки | порты (`PlanPorts` / `PrepareContext.host_ctx`) |
| Выполнение шагов (git, lock, env, шаблон compose) | [`BootstrapHandle`](../../dev_project/host/ports.py): `git_repos`, `env_resolver`, `pd_manager`, … |
| Генератор `odoo.conf` | `bootstrap.odoo_conf` (на handle уже есть; прямые вызовы / следующие шаги — сюда, не в `config._odoo_conf`) |
| Сырой `bootstrap.config` | только пока нет метода на handle (drift, сборка compose-сервиса) |

Новые шаги и фичи **не** добавляют плоские свойства на `Config` «для удобства».

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
| Живой runtime-фасад | `HostRuntimeState` / mixin | Команда compose, capabilities — состояние **сеанса**, не описание проекта |

Сборка по фазам: [`bootstrap.py`](../../dev_project/config/bootstrap.py).

## Отличие от соседних карт

- [Зоны подготовки](prepare-zones.md) — **шаги** `prepare` / `plan` (git, карта папок, compose).
- [Движок запуска](runtime-backend.md) — **как поднять стек** после prepare.
- Эта страница — **из чего состоит снимок Config** и через какие порты к нему ходить.

## Связанные документы

- [ADR-003](adr-003-host-ports-vs-config.md) — порты vs Config
- [ADR-030](adr-030-config-as-assembler.md) — Config как сборщик
- [cli-architecture.md](cli-architecture.md) — маршрутизация команд
