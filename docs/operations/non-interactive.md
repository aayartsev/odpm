# Запуск без интерактивных вопросов

Если стандартный ввод **не подключён к терминалу** (нет TTY), odpm **не задаёт вопросов** через `input()`. Так работают скрипты, задачи cron и многие системы непрерывной интеграции.

## Что подготовить заранее

**Файл `.env`** в каталоге проекта или в `~/.odpm/.env`.

Либо задайте **хотя бы одну** переменную из списка в окружении процесса — odpm создаст `~/.odpm/.env`, подставив остальное по умолчанию:

- `BACKUP_DIR`, `ODOO_PROJECTS_DIR`
- `ODOO_PORT`, `POSTGRES_PORT`, `DEBUGGER_PORT`, `GEVENT_PORT`
- `ODPM_SCENARIO`, `ODPM_LOCALE`
- `PATH_TO_SSH_KEY` (при необходимости)

## Инициализация и `odpm.json`

При `--init` без готового `odpm.json` в разрабатываемом репозитории укажите **`--odoo-version`** или положите `odoo_version` в репозиторий до запуска.

## Manifest с `${VAR}`

Если в `odpm.json` или `user_settings.json` используются `${ИМЯ}`, задайте значения **до** запуска:

| Способ | Пример |
|--------|--------|
| project `.env` | `ODOO_PLATFORM_DIR=/data/odoo/19.0` |
| `export` в shell / CI | `export GIT_HOST=git.corp.example` |
| default в manifest | `"file://${PATH:-/opt/odoo}"` |

Координатор проекта документирует обязательные имена для команды и CI — см. [роль координатора](../scenarios/team-coordinator.md). Отсутствующая переменная без default завершает odpm с ошибкой.

## Database drift в CI и скриптах

Без TTY odpm **не задаёт** вопросов о расхождении конфигурации PostgreSQL. Если обнаружен blocking drift (`data_path`, `postgres_major`, `app_role_missing` и др.), запуск завершится ошибкой.

Варианты:

1. Один раз разрешить drift из интерактивного терминала (`odpm` или `odpm plan`).
2. Явно принять вид drift: **`--accept-database-drift=KIND`** (флаг можно повторять для нескольких KIND).
3. Перед стеком восстановить роль: `odpm database ensure-role` (postgres должен быть запущен).

Пример:

```bash
odpm --accept-database-drift=odpm_scenario --skip-start
odpm database ensure-role
odpm -d test_db -i -u
```

Подробнее: [состояние PostgreSQL](../reference/database-state.md).

## Пример для сценария сборки образа

```bash
export ODPM_SCENARIO=ci
export ODOO_PROJECTS_DIR=/data/odoo_projects
export BACKUP_DIR=/data/backups
odpm --init https://github.com/example/demo.git --skip-start
```
