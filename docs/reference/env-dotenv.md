# Переменные файла `.env`

Файл **`.env`** задаёт параметры **этого** каталога odpm-окружения: порты, сценарий, пути к резервным копиям и клонам git. Если он лежит **в каталоге проекта**, он **полностью заменяет** `~/.odpm/.env` — значения из двух файлов не смешиваются ([иерархия](config-hierarchy.md)).

При **первом интерактивном** запуске odpm задаёт вопросы мастера настройки и записывает ответы в `.env` (глобальный или проектный). На незнакомые пункты можно нажать Enter.

## Переменные

| Переменная | Назначение | Значение по умолчанию |
|------------|------------|------------------------|
| `BACKUP_DIR` | Каталог архивов баз (`--db-backup`, `--db-restore`) | `~/odoo_backups` |
| `ODOO_PROJECTS_DIR` | Куда клонировать platform и git-зависимости | `~/odoo_projects` |
| `ODOO_PORT` | HTTP-порт Odoo на компьютере | `8069` |
| `POSTGRES_PORT` | Порт PostgreSQL на компьютере (в сценарии `server` — только localhost) | `5432` |
| `POSTGRES_SERVICE_NAME` | Имя сервиса PostgreSQL в `docker-compose.yml` и `db_host` в `odoo.conf` (без `ODPM_COMPOSE_PREFIX`) | `db` |
| `ODPM_COMPOSE_PREFIX` | Префикс для **полной** изоляции compose-стека: ключи `db`/`odoo`, том `postgres-data`, имя проекта Docker Compose | не задан |
| `DEBUGGER_PORT` | Порт отладчика; см. [семантику по backend](#debugger_port-backend) | `5678` |
| `ODPM_DEBUGGER_BACKEND` | `debugpy_listen` или `pydevd_connect` | `debugpy_listen` |
| `ODPM_IDE` | Какие настройки IDE генерировать: `vscode`, `pycharm`, `both`, `none` | `vscode` |
| `ODPM_DEBUGGER_CONNECT_HOST` | Хост IDE для `pydevd_connect` (откуда контейнер подключается к Debug Server) | `host.docker.internal` |
| `ODPM_DEBUGGER_SUSPEND` | `1` / `y` — Odoo ждёт IDE после `settrace` (`pydevd_connect`) | `0` |
| `GEVENT_PORT` | Порт веб-сокетов gevent | `8072` |
| `ODPM_SCENARIO` | `developer`, `server` или `ci` | `developer` |
| `ODPM_LOCALE` | Язык сообщений odpm, напр. `ru_RU` | берется из системы | см. [locale.md](locale.md) |
| `PATH_TO_SSH_KEY` | Путь к ключу SSH для git (редко нужен) | пусто |

Смена `POSTGRES_SERVICE_NAME`, `POSTGRES_PORT` или `ODPM_COMPOSE_PREFIX` относительно сохранённого снимка даёт **database drift** — см. [состояние PostgreSQL](database-state.md).

## `DEBUGGER_PORT` и backend

| `ODPM_DEBUGGER_BACKEND` | Что означает `DEBUGGER_PORT` | Compose |
|-------------------------|------------------------------|---------|
| **`debugpy_listen`** | Порт **в контейнере**, publish на хост (`5678:5678`) | IDE подключается к `localhost:DEBUGGER_PORT` |
| **`pydevd_connect`** | Порт **Debug Server на хосте** (PyCharm слушает) | Порт **не** публикуется; нужен `extra_hosts` для `host.docker.internal` на Linux |

Подробный workflow: [отладка в IDE](../operations/vscode-debug.md).

Поля `ODPM_DEBUGGER_CONNECT_HOST` и `ODPM_DEBUGGER_SUSPEND` попадают в `.odpm/runtime/config.json` всегда; для `debugpy_listen` runtime их не использует.

## Примеры

### VS Code / Cursor (по умолчанию)

```ini
DEBUGGER_PORT=5678
ODPM_DEBUGGER_BACKEND=debugpy_listen
ODPM_IDE=vscode
```

### PyCharm Debug Server

```ini
DEBUGGER_PORT=5678
ODPM_DEBUGGER_BACKEND=pydevd_connect
ODPM_IDE=pycharm
ODPM_DEBUGGER_CONNECT_HOST=host.docker.internal
ODPM_DEBUGGER_SUSPEND=1
```

### Полный фрагмент `.env`

```ini
BACKUP_DIR=/home/user/odoo_backups
ODOO_PROJECTS_DIR=/home/user/odoo_projects
PATH_TO_SSH_KEY=
ODOO_PORT=8069
POSTGRES_PORT=5432
POSTGRES_SERVICE_NAME=db
DEBUGGER_PORT=5678
ODPM_DEBUGGER_BACKEND=debugpy_listen
ODPM_IDE=vscode
GEVENT_PORT=8072
ODPM_SCENARIO=developer
ODPM_LOCALE=ru_RU
```

## SSH и git

Мастер настройки **не спрашивает** путь к SSH-ключу. Обычно достаточно настройки OpenSSH (`~/.ssh/config`, ssh-agent).

Переменная **`PATH_TO_SSH_KEY`** нужна, если git не может использовать стандартный SSH (типично на изолированной машине сборки):

```ini
PATH_TO_SSH_KEY=/home/user/.ssh/id_ed25519
```

Один ключ применяется ко всем указанным удалённым репозиториям.

## `POSTGRES_SERVICE_NAME`

Имя сервиса PostgreSQL в `docker-compose.yml` и значение `db_host` в `odoo.conf` (DNS внутри docker-сети). Допустимы строчные буквы, цифры, `_` и `-`; имя должно начинаться с буквы. После смены перегенерируйте `docker-compose.yml` и `odoo.conf` (обычный запуск `odpm`).

**Не используется**, если задан **`ODPM_COMPOSE_PREFIX`** — postgres получает имя `{prefix}db` (например `acme-db`), с предупреждением в логе.

## `ODPM_COMPOSE_PREFIX`

Опциональный префикс для **изоляции полного compose-стека** на общем хосте: несколько odpm-проектов в одном каталоге или параллельные копии без коллизий имён сервисов, томов и scope Docker Compose.

| Режим | Поведение |
|-------|-----------|
| **Не задан** | Как в 4.6: postgres — из `POSTGRES_SERVICE_NAME` (по умолчанию `db`), odoo — `odoo`, том — `postgres-data` |
| **Задан** (`acme` или `acme-`) | Сервисы `acme-db`, `acme-odoo`; том `acme-postgres-data`; project name / `docker compose -p` — `acme` |

Нормализация: lowercase, символы `[a-z0-9-]`, имя начинается с буквы; завершающий `-` в `.env` опционален. Невалидное значение **игнорируется** (префикс отключён, warning в логе).

В `odpm.json` sidecar по-прежнему указывают логические имена (`depends_on: ["db"]`); odpm переписывает их в physical при генерации `docker-compose.yml`.

Пример:

```ini
ODPM_COMPOSE_PREFIX=acme
```

См. [ADR-012](../contributing/adr-012-compose-service-prefix.md), [состояние PostgreSQL](database-state.md).

## Переменные для подстановки в manifest

Помимо встроенных ключей odpm в `.env` можно задавать **произвольные** имена для `${VAR}` в `odpm.json` и `user_settings.json` (например `ODOO_PLATFORM_DIR`, `OCA_WEB_PATH`, `GIT_HOST`). Они **не** управляют портами или сценарием сами по себе — только подставляются в whitelist-поля manifest при чтении JSON.

Приоритет для `${VAR}`: переменные **процесса** odpm перекрывают project `.env`. Пустой default в manifest: `${VAR:-}`.

Типичный фрагмент project `.env` для локальной разработки:

```ini
ODOO_PLATFORM_DIR=/home/dev/odoo/19.0
DEVELOPING_PROJECT_DIR=/home/dev/my_addons
OCA_WEB_PATH=/home/dev/src/oca/web
GIT_HOST=git.company.example
```

См. [odpm.json](odpm-json.md), [user_settings.json](user-settings.md), [иерархия конфигурации](config-hierarchy.md).
