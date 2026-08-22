# Переменные файла `.env`

Параметры odpm-окружения (порты, сценарий, пути к бэкапам и клонам git) задаются в **`.env`**. С **4.7** при чтении odpm объединяет два файла ([иерархия](config-hierarchy.md), [ADR-013](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-013-layered-env-dotenv.md)):

| Файл | Роль |
|------|------|
| `~/.odpm/.env` | Общий профиль пользователя (база) |
| `.env` в каталоге проекта | Переопределения для **этого** окружения (overlay, сильнее home) |

Мастер первого запуска **записывает** в project `.env`, если файл уже есть, иначе в `~/.odpm/.env`. В project можно держать только отличающиеся ключи (например `ODOO_PORT` и `ODPM_COMPOSE_PREFIX`), а `BACKUP_DIR` и `ODOO_PROJECTS_DIR` — в home.

При **первом интерактивном** запуске odpm задаёт вопросы мастера настройки. На незнакомые пункты можно нажать Enter.

### Пример: общее в home, своё в project

`~/.odpm/.env`:

```ini
BACKUP_DIR=/home/dev/backups
ODOO_PROJECTS_DIR=/home/dev/odoo_projects
PATH_TO_SSH_KEY=/home/dev/.ssh/id_ed25519
ODPM_LOCALE=ru_RU
```

`<project>/.env`:

```ini
ODOO_PORT=8070
ODPM_COMPOSE_PREFIX=acme
ODOO_PLATFORM_DIR=/work/client/odoo/19.0
```

## Переменные

| Переменная | Назначение | Значение по умолчанию |
|------------|------------|------------------------|
| `BACKUP_DIR` | Каталог архивов баз (`--db-backup`, `--db-restore`) | `~/odoo_backups` |
| `ODOO_PROJECTS_DIR` | Куда клонировать platform и git-зависимости | `~/odoo_projects` |
| `ODOO_PORT` | HTTP-порт Odoo на компьютере | `8069` |
| `POSTGRES_PORT` | Порт PostgreSQL на компьютере (в сценарии `server` — только localhost) | `5432` |
| `POSTGRES_SERVICE_NAME` | Имя сервиса PostgreSQL в `docker-compose.yml` и `db_host` в `odoo.conf` (без `ODPM_COMPOSE_PREFIX`) | `db` |
| `ODPM_COMPOSE_PREFIX` | Префикс для **полной** изоляции compose-стека: ключи `db`/`odoo`, том `postgres-data`, имя проекта Docker Compose | не задан |
| `ODPM_COMPOSE_NETWORK` | Логическое имя **одной** compose-сети для всего стека (managed bridge или external); без значения — implicit default network | не задан |
| `ODPM_COMPOSE_NETWORK_EXTERNAL` | `1` / `true` — сеть уже существует на хосте (`external: true`); без prefix на имени | `0` |
| `DEBUGGER_PORT` | Порт отладчика; см. [семантику по backend](#debugger_port-backend) | `5678` |
| `ODPM_DEBUGGER_BACKEND` | `debugpy_listen` или `pydevd_connect` | `debugpy_listen` |
| `ODPM_IDE` | Какие настройки IDE генерировать: `vscode`, `pycharm`, `both`, `none` | `vscode` |
| `ODPM_DEBUGGER_CONNECT_HOST` | Хост IDE для `pydevd_connect` (откуда контейнер подключается к Debug Server) | `host.docker.internal` |
| `ODPM_DEBUGGER_SUSPEND` | `1` / `y` — Odoo ждёт IDE после `settrace` (`pydevd_connect`) | `0` |
| `GEVENT_PORT` | Порт веб-сокетов gevent | `8072` |
| `ODPM_SCENARIO` | `developer`, `server` или `ci` | `developer` |
| `ODPM_CI_IMAGE_BUILDER` | Бэкенд `--build-image`: `docker` или `kaniko` (слабее CLI `--image-builder`; читается из layered `.env`, ADR-017) | `docker` |
| `ODPM_CI_IMAGE_PUSH` | `1` / `true` / `yes` — push после `--build-image` (как `--image-push`) | выкл. |
| `ODPM_KANIKO_EXECUTOR_MODE` | `docker-run` или `direct` (мастер для `ci`+kaniko предлагает `direct` по умолчанию) | `docker-run` |
| `ODPM_KANIKO_EXECUTOR_IMAGE` | Образ executor для режима `docker-run` | `gcr.io/kaniko-project/executor:v1.23.2` |
| `ODPM_KANIKO_EXECUTOR_BIN` | Бинарь executor для режима `direct` | `executor` |
| `ODPM_KANIKO_EXECUTOR_WRAPPER` | Опциональный префикс argv для `direct` (скрипт, запускающий executor от root); рекомендуется на non-root CI | пусто |
| `ODPM_KANIKO_EXECUTOR_EXTRA_FLAGS` | Доп. флаги Kaniko executor (напр. `--kaniko-dir=/tmp/kaniko`) | пусто |
| `ODPM_KANIKO_EXECUTOR_SUDO` | `1` / `true` / `yes` — prepend `sudo -n` перед executor в `direct`, если wrapper не задан; нужен passwordless sudo | выкл. |
| `ODPM_BASE_IMAGE_REGISTRY` | Prefикс registry для base image при `kaniko` (обязателен для daemonless base) | пусто |
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

В `odpm.json` sidecar по-прежнему указывают логические имена (`depends_on: ["db"]`); odpm переписывает их в physical при генерации `docker-compose.yml`. Для hostname внутри `environment` / `command` используйте **`${@service:db}`** / **`${@service:odoo}`** — в YAML попадёт уже physical имя (`acme-db`). Sidecar-ключи без префикса резолвятся в то же имя.

Пример:

```ini
ODPM_COMPOSE_PREFIX=acme
```

См. [ADR-012](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-012-compose-service-prefix.md), [состояние PostgreSQL](database-state.md), [подстановку в `odpm.json`](odpm-json.md).

## `ODPM_COMPOSE_NETWORK` / `ODPM_COMPOSE_NETWORK_EXTERNAL`

Опционально объявить **одну** именованную Docker Compose-сеть для **всего** odpm-стека (`db`, `odoo`, sidecars). Без этих переменных odpm **не** добавляет секцию `networks:` в `docker-compose.yml` — сервисы остаются в implicit default network проекта (как в 4.6).

| Режим | `.env` | Поведение |
|-------|--------|-----------|
| **По умолчанию** | переменные не заданы | Без `networks:` в YAML |
| **Managed** | `ODPM_COMPOSE_NETWORK=stack` | `networks: { stack: { driver: bridge } }`, все сервисы без своего `networks` подключаются |
| **External** | `ODPM_COMPOSE_NETWORK=proxy` + `ODPM_COMPOSE_NETWORK_EXTERNAL=1` | `external: true`; имя **без** prefix (общая сеть reverse proxy) |

С **`ODPM_COMPOSE_PREFIX=acme`** managed-сеть `stack` становится physical **`acme-stack`**; external `proxy` остаётся `proxy`.

Нормализация имени: как у prefix (`[a-z0-9-]`, с буквы). Невалидное значение отключает сеть (warning). `ODPM_COMPOSE_NETWORK_EXTERNAL` без имени сети не действует.

Типичный split ([ADR-013](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-013-layered-env-dotenv.md)):

`~/.odpm/.env`:

```ini
ODPM_COMPOSE_NETWORK=proxy
ODPM_COMPOSE_NETWORK_EXTERNAL=1
```

`<project>/.env`:

```ini
ODPM_COMPOSE_PREFIX=acme
ODPM_COMPOSE_NETWORK=stack
```

Sidecar в manifest с `networks: ["stack"]` согласован только при `ODPM_COMPOSE_NETWORK=stack`; иначе `odpm manifest validate` выдаёт warning. См. [плагины](plugins.md), [ADR-014](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-014-compose-stack-network.md).

Смена сети **не** даёт database drift (не в снимке `last_run.json`); перегенерируется `docker-compose.yml` при следующем materialize.

## Переменные для подстановки в manifest

Помимо встроенных ключей odpm в `.env` можно задавать **произвольные** имена для `${VAR}` в `odpm.json` и `user_settings.json` (например `ODOO_PLATFORM_DIR`, `OCA_WEB_PATH`, `GIT_HOST`). Они **не** управляют портами или сценарием сами по себе — только подставляются в whitelist-поля manifest при чтении JSON.

Приоритет для `${VAR}`: переменные **процесса** odpm перекрывают effective `.env` (merge home + project). Пустой default в manifest: `${VAR:-}`.

Типичный фрагмент project `.env` для локальной разработки:

```ini
ODOO_PLATFORM_DIR=/home/dev/odoo/19.0
DEVELOPING_PROJECT_DIR=/home/dev/my_addons
OCA_WEB_PATH=/home/dev/src/oca/web
GIT_HOST=git.company.example
```

См. [odpm.json](odpm-json.md), [user_settings.json](user-settings.md), [иерархия конфигурации](config-hierarchy.md).
