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

## Сценарий `server` без исходников платформы

Если на диске ещё **нет** каталога с `odoo-bin`, в интерактивном режиме odpm может предложить скачать nightly-архив. **Без TTY** будет **немедленная ошибка**.

Варианты:

- заранее заполнить каталог platform (через сценарий `developer` и git);
- один раз выполнить подготовку из обычного терминала;
- не использовать `server` для самого первого клонирования platform.

## Manifest с `${VAR}`

Если в `odpm.json` или `user_settings.json` используются `${ИМЯ}`, задайте значения **до** запуска:

| Способ | Пример |
|--------|--------|
| project `.env` | `ODOO_PLATFORM_DIR=/data/odoo/19.0` |
| `export` в shell / CI | `export GIT_HOST=git.corp.example` |
| default в manifest | `"file://${PATH:-/opt/odoo}"` |

Координатор проекта документирует обязательные имена для команды и CI — см. [роль координатора](../scenarios/team-coordinator.md). Отсутствующая переменная без default завершает odpm с ошибкой.

## Пример для сценария сборки образа

```bash
export ODPM_SCENARIO=ci
export ODOO_PROJECTS_DIR=/data/odoo_projects
export BACKUP_DIR=/data/backups
odpm --init https://github.com/example/demo.git --skip-start
```
