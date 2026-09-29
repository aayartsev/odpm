# Параметры командной строки

Команда **`odpm`** (или `python3 …/odpm.py`) принимает параметры, которые задают **одноразовое** поведение: инициализацию, работу с базой, сборку образа, план изменений. Полный список с краткими подсказками на английском: `odpm --help`.

Ниже — справочник по группам на русском языке. Имена флагов приведены **как в программе** (латиница).

## Инициализация проекта

| Параметр | Описание |
|----------|----------|
| `--init ССЫЛКА` | Сделать текущий каталог odpm-проектом. Ссылка: HTTPS, `git@…`, `file:///…` |
| `--branch ИМЯ` | Вместе с `--init`: ветка **разрабатываемого** репозитория |
| `--odoo-version ВЕР` | Версия Odoo (например `19.0`) в `odpm.json` |
| `--odoo-git-link ССЫЛКА` | Репозиторий **платформы** вместо официального odoo/odoo |
| `--platform-name ИМЯ` | Имя Python-пакета форка (по умолчанию `odoo`) |
| `--python-version ВЕР` | Версия Python в образе |
| `--distro-name ИМЯ` | Имя дистрибутива Linux (сейчас `debian`) |
| `--distro-version ВЕР` | Версия дистрибутива (`11`, `12`, …) |
| `--postgres-version ВЕР` | Версия PostgreSQL в compose |
| `--requirements-txt ПАКЕТЫ` | Пакеты Python через запятую → запись в `odpm.json` |
| `--secrets-file ПУТЬ` | Импорт JSON v1 в `.odpm/secrets.json` (при `--init` и на любом запуске; early bootstrap, до expand `${@secret:}` в `user_settings`). Подразумевает провайдер `file`. См. [локальные секреты](../operations/secrets.md). |
| `--secrets-provider ИМЯ` | Провайдер секретов на этот запуск (`file`, `infisical` или id плагина). Сильнее `ODPM_SECRETS_PROVIDER` и `secrets.provider.type`. `--secrets-file` выставляет `file`. |
| `--security-profile ИМЯ` | Профиль безопасности (`convenience` / `hardened`). Сильнее `ODPM_SECURITY_PROFILE`; иначе дефолт от `ODPM_SCENARIO`. См. [безопасность](../operations/security.md). |

Пример:

```bash
odpm --init https://github.com/aayartsev/odoo_demo_project.git --branch 19.0 \
  --odoo-version 19.0 --python-version 3.12 --distro-version 12
```

Импорт секретов при развёртывании:

```bash
odpm --init file:///path/to/my_addons \
  --secrets-file /secure/client-secrets.json

# ротация ключей на существующем проекте
odpm --secrets-file ~/new-secrets.json --skip-start
```

## Подготовка окружения и образ

| Параметр | Описание |
|----------|----------|
| `--skip-start` | Пересоздать Docker-файлы и compose **без** запуска контейнеров; при наличии lock — выбор ревизий по файлу фиксации |
| `--update-lock` | Записать `.odpm/deps.lock.json` и завершить работу |
| `--no-git-update` | Не трогать git; lock **не читается**; каталоги должны уже существовать |
| `--build-image` | Собрать образ для сценария **`ci`** (иначе ошибка) |
| `--image-tag МЕТКА` | Имя и тег образа Docker для `--build-image` |
| `--image-builder {docker,kaniko}` | Бэкенд сборки CI-образа (по умолчанию `docker`; перекрывает `ODPM_CI_IMAGE_BUILDER`) |
| `--image-push` | После сборки опубликовать образ (`docker push` / kaniko `--destination`) |
| `--version` | Показать версию odpm |

## План изменений (пробный прогон)

Показывает, какие шаги подготовки выполнились бы, **без** изменения git, записи файлов и `docker compose up`.

```bash
odpm plan --skip-start
odpm plan --plan-format json | jq .
odpm plan --plan-show-diff --skip-start
```

Устаревший синоним: `--plan` (лучше подкоманда `plan`).

| Параметр | Описание |
|----------|----------|
| `--plan-format {table,json}` | Таблица в журнал или JSON в stdout |
| `--plan-strict` | Код возврата 1, если обязательный шаг — изменение |
| `--plan-show-diff` | Показать отличия в runtime config, compose, dockerignore |
| `--plan-no-docker` | Не опрашивать Docker о состоянии контейнеров |

Среди шагов подготовки есть **`database.drift`** — сравнение конфигурации PostgreSQL со снимком `last_run.json`. См. [состояние PostgreSQL](database-state.md).

## Подкоманда `database`

Инспекция локального **кластера PostgreSQL**, роли приложения и **скачивание remote backup** через Odoo manager:

```bash
odpm database status
odpm database status --format json
odpm database ensure-role
ODPM_REMOTE_DB_MASTER_PWD='…' odpm database pull --url https://client.example.com --remote-db prod
```

| Команда | Описание |
|---------|----------|
| `database status` | Fingerprints, drift, проверка контейнера postgres и роли приложения |
| `database status --format json` | То же в JSON |
| `database ensure-role` | Создать или обновить роль приложения в запущенном PostgreSQL |
| `database pull` | Скачать zip с `{URL}/web/database/backup` в `BACKUP_DIR` (пароль только из env `ODPM_REMOTE_DB_MASTER_PWD`) |

`database pull` нужен каталог проекта odpm с `BACKUP_DIR` в `.env`; compose up для самого download не требуется. На stdout печатается только имя архива. Предназначено для сценариев **developer** / **server**, не для типичного CI.

Флаг **`--accept-database-drift=KIND`** (повторяемый) — принять drift без интерактивного prompt. KIND: `data_path`, `postgres_major`, `app_role_missing`, `odpm_scenario`, `data_dir_empty_changed`.

Подробнее о локальном кластере: [состояние PostgreSQL и drift](database-state.md). Remote pull + restore: [рецепты](recipes.md) (`pull-remote-db`).

## Подкоманда `modules`

Списки модулей для `-i`/`-u` из git-истории developing и маркер последнего apply:

```bash
odpm modules diff
odpm modules diff --diff-base @last-applied --format shell
odpm modules record-applied
```

| Команда | Описание |
|---------|----------|
| `modules diff` | Init/update CSV с `BASE...HEAD`; `--diff-base`, `--format {text,shell,json}` |
| `modules record-applied` | Записать HEAD developing в `.odpm/deploy/last_applied.json` |

Подробнее и shell-рецепт: [маркер деплоя](deploy-marker.md).

## Подкоманда `run`

Именованные рецепты (повторный вызов odpm):

```bash
odpm run --list
odpm run apply-modules-from-diff -d prod_db
odpm run apply-modules-from-diff -d prod_db --dry-run
```

Подробнее: [рецепты](recipes.md), [маркер деплоя](deploy-marker.md).

## База данных и модули

| Параметр | Описание |
|----------|----------|
| `-d ИМЯ_БД` | Имя базы; при отсутствии — создание по `db_creation_data` |
| `-i [МОДУЛИ]` | Без значения — модули из `init_modules`; с CSV (напр. `sale,crm`) — список с CLI (приоритет над settings) |
| `-u [МОДУЛИ]` | Без значения — модули из `update_modules`; с CSV — список с CLI (приоритет над settings) |
| `-t`, `--test` | Запустить тесты модулей; нужны `-d` и обычно `-i` или `-u` |
| `--screencasts` | С `-t`: сохранять видео при ошибках туров |
| `--odoo-bin АРГУМЕНТЫ…` | Передать аргументы исполняемому файлу Odoo, напр. `--stop-after-init` |

```bash
odpm -d test_db -i -u
odpm -d test_db -i sale,crm -u my_module
odpm -d test_db -i --odoo-bin --stop-after-init
```

## Дата ночной сборки платформы

| Параметр | Описание |
|----------|----------|
| `--odoo-build-date ДАТА` | `ГГГГММДД` или `ГГГГ-ММ-ДД`; перекрывает `odoo_build_date` в json |

## Обслуживание базы

| Параметр | Описание |
|----------|----------|
| `--get-dbs-list` | Список баз |
| `--db-backup [АРХИВ]` | Резервная копия базы `-d` в `BACKUP_DIR` |
| `--db-restore АРХИВ` | Восстановить архив в базу `-d` |
| `--db-drop` | Удалить Odoo-базу `-d`; с `-i`/`-u` — пересоздать и установить модули. На legacy-кластере с чужим PostgreSQL-owner odpm выполняет прямой `DROP DATABASE` |

## Переводы и администратор

| Параметр | Описание |
|----------|----------|
| `--translate ЯЗЫК` | Обновить переводы (напр. `ru_RU`) |
| `--export-po-files ЯЗЫК` | Экспорт pot/po для модулей из `update_modules`, либо из `-u CSV`, если задан |
| `--set-admin-pass` | Логин/пароль admin из `db_default_admin_*`; нужен `-d` |

## Прочие инструменты разработчика

| Параметр | Описание |
|----------|----------|
| `--start-precommit` | Запустить pre-commit в разрабатываемом проекте в контейнере |
| `--sql-execute` | Выполнить SQL из `sql_queries`; нужен `-d` |

## Подкоманда `scaffold`

Создание каркаса нового модуля (без других флагов odpm):

```bash
odpm scaffold имя_модуля
odpm scaffold имя_модуля -t /путь/к/шаблонам
```

| Параметр | Описание |
|----------|----------|
| `scaffold ИМЯ` | Генерация модуля по шаблонам Jinja2 |
| `-t`, `--scaffold_template_name` | Каталог своих шаблонов |

Фиксация версий git: [deps.lock.json](deps-lock.md).
