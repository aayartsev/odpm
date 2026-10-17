# Параметры командной строки

Команда **`odpm`** (или `python3 …/odpm.py`) принимает **подкоманды** и флаги для одноразового поведения: подъём стека, подготовка файлов, init, сборка образа, работа с базой. Полный список: `odpm --help` или `odpm -V` / `odpm --version` для версии.

Ниже — справочник по группам. Имена флагов **как в программе** (латиница).

## Дерево команд

| Команда | Смысл |
|---------|--------|
| `odpm up` | Подготовить файлы и поднять compose-стек (в т.ч. `-i`/`-u`, комбо `--db-restore`) |
| `odpm prepare` | Только файлы / lock, **без** контейнеров (вместо `--skip-start`) |
| `odpm init URL` | Инициализация проекта (вместо `--init`) |
| `odpm build` | Сборка CI-образа (вместо `--build-image`) |
| `odpm plan` | Пробный прогон шагов |
| `odpm database …` | Host: `status` / `ensure-role` / `pull`. Стек: `backup` / `restore` / `drop` / `list` |
| `odpm modules …` | Diff / record-applied |
| `odpm run …` | Рецепты |
| `odpm manifest …` | migrate / validate |
| `odpm scaffold …` | Каркас модуля |
| `-V`, `--version` | Версия odpm (глобально) |

В **4.8** голый `odpm` и старые корневые флаги ещё работают с **предупреждением**. В **5.0** голый `odpm` покажет справку по подкомандам (без подъёма стека). См. [Устарело в 4.8](#устарело-в-48).

## Инициализация проекта

Предпочтительно: **`odpm init URL`**. Устаревший синоним: `--init ССЫЛКА`.

| Параметр | Описание |
|----------|----------|
| `odpm init ССЫЛКА` / `--init ССЫЛКА` | Сделать текущий каталог odpm-проектом. Ссылка: HTTPS, `git@…`, `file:///…` |
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
odpm init https://github.com/aayartsev/odoo_demo_project.git --branch 19.0 \
  --odoo-version 19.0 --python-version 3.12 --distro-version 12
```

Импорт секретов при развёртывании:

```bash
odpm init file:///path/to/my_addons \
  --secrets-file /secure/client-secrets.json

# ротация ключей на существующем проекте
odpm prepare --secrets-file ~/new-secrets.json
```

## Подготовка окружения и образ

| Команда / параметр | Описание |
|--------------------|----------|
| `odpm prepare` | Пересоздать Docker-файлы и compose **без** запуска контейнеров |
| `odpm prepare --update-lock` | Записать `.odpm/deps.lock.json` и завершить работу |
| `--no-git-update` | Не трогать git; lock **не читается**; каталоги должны уже существовать |
| `odpm build` | Собрать образ для сценария **`ci`** (иначе ошибка) |
| `--image-tag МЕТКА` | Имя и тег образа Docker для `odpm build` |
| `--image-builder {docker,kaniko}` | Бэкенд сборки CI-образа (по умолчанию `docker`) |
| `--image-push` | После сборки опубликовать образ |
| `-V`, `--version` | Показать версию odpm |

Устаревшие синонимы: `--skip-start` → `odpm prepare`; `--build-image` → `odpm build`.

## План изменений (пробный прогон)

Показывает, какие шаги подготовки выполнились бы, **без** изменения git, записи файлов и `docker compose up`.

```bash
odpm plan
odpm plan --plan-format json | jq .
odpm plan --plan-show-diff --update-lock
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

**На хосте** (без подъёма стека): инспекция кластера PostgreSQL, роль приложения, скачивание remote backup.

**Через стек** (prepare + compose up + контейнер): `backup` / `restore` / `drop` / `list`. Комбо restore+модули — только через `odpm up`.

```bash
odpm database status
odpm database status --format json
odpm database ensure-role
ODPM_REMOTE_DB_MASTER_PWD='…' odpm database pull --url https://client.example.com --remote-db prod
odpm database list
odpm database backup -d test_db
odpm database restore -d test_db archive.zip
odpm database drop -d test_db
```

| Команда | Описание |
|---------|----------|
| `database status` | Fingerprints, drift, проверка контейнера postgres и роли приложения |
| `database status --format json` | То же в JSON |
| `database ensure-role` | Создать или обновить роль приложения в запущенном PostgreSQL |
| `database pull` | Скачать zip с `{URL}/web/database/backup` в `BACKUP_DIR` (пароль из `ODPM_REMOTE_DB_MASTER_PWD`) |
| `database list` | Список Odoo-баз через стек |
| `database backup -d …` | Резервная копия через стек |
| `database restore -d … АРХИВ` | Восстановление через стек (без `-i`/`-u`) |
| `database drop -d …` | Удаление базы через стек |

`database pull` — **примитив**: compose up для download не требуется. Логи — в stderr, **на stdout только имя архива**. Пример полного пайплайна:

```bash
export ODPM_REMOTE_DB_MASTER_PWD='…'
ARCHIVE=$(odpm database pull --url https://client.example.com --remote-db prod)
odpm up -d test_db --db-restore "$ARCHIVE" -i -u --set-admin-pass
```

Shortcut pull+restore без своих шагов: builtin [`odpm run pull-remote-db`](recipes.md#builtin-pull-remote-db). YAML-рецепты **не** подставляют stdout предыдущего шага — для цепочек с именем архива используйте shell. Предназначено для **developer** / **server**, не для типичного CI.

Флаг **`--accept-database-drift=KIND`** (повторяемый) — принять drift без интерактивного prompt. KIND: `data_path`, `postgres_major`, `app_role_missing`, `odpm_scenario`, `data_dir_empty_changed`.

Подробнее о локальном кластере: [состояние PostgreSQL и drift](database-state.md). Remote pull: [рецепты](recipes.md) (примитив + `pull-remote-db`).

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

## База данных и модули (`odpm up`)

Флаги ниже — на **`odpm up`** (и пока на голом `odpm` с предупреждением в 4.8).

| Параметр | Описание |
|----------|----------|
| `-d ИМЯ_БД` | Имя базы; при отсутствии — создание по `db_creation_data` |
| `-i [МОДУЛИ]` | Без значения — модули из `init_modules`; с CSV (напр. `sale,crm`) — список с CLI |
| `-u [МОДУЛИ]` | Без значения — модули из `update_modules`; с CSV — список с CLI |
| `-t`, `--test` | Запустить тесты модулей; нужны `-d` и обычно `-i` или `-u` |
| `--screencasts` | С `-t`: сохранять видео при ошибках туров |
| `--odoo-bin АРГУМЕНТЫ…` | Передать аргументы исполняемому файлу Odoo, напр. `--stop-after-init` |

```bash
odpm up -d test_db -i -u
odpm up -d test_db -i sale,crm -u my_module
odpm up -d test_db -i --odoo-bin --stop-after-init
```

## Дата ночной сборки платформы

| Параметр | Описание |
|----------|----------|
| `--odoo-build-date ДАТА` | `ГГГГММДД` или `ГГГГ-ММ-ДД`; перекрывает `odoo_build_date` в json |

## Обслуживание базы

Предпочтительно подкоманды `odpm database …`. На **`odpm up`** флаги ниже нужны для **комбо** (несколько операций и/или `-i`/`-u`).

| Параметр | Описание |
|----------|----------|
| `--get-dbs-list` | Список баз (или `odpm database list`) |
| `--db-backup [АРХИВ]` | Резервная копия базы `-d` (или `odpm database backup`) |
| `--db-restore АРХИВ` | Восстановить архив в базу `-d` (или `odpm database restore`); с `-i`/`-u` — только через `odpm up` |
| `--db-drop` | Удалить Odoo-базу `-d`; с `-i`/`-u` — пересоздать и установить модули |

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

## Устарело в 4.8

Старые вызовы ещё работают и печатают предупреждение. Предпочтительные формы:

| Устарело | Новое |
|----------|--------|
| голый `odpm` | `odpm up` (в **5.0** голый `odpm` → справка по подкомандам) |
| `odpm -d … -i …` | `odpm up -d … -i …` |
| `odpm --skip-start` | `odpm prepare` |
| `odpm --init URL` | `odpm init URL` |
| `odpm --build-image` | `odpm build` |
| `odpm --plan` | `odpm plan` |
| один `--db-backup` / `--db-restore` / `--db-drop` / `--get-dbs-list` | `odpm database backup\|restore\|drop\|list` |
| `--db-drop --db-restore …` или restore+`-i` | `odpm up …` |

Контракт: [ADR-026](../contributing/adr-026-cli-command-verbs.md).
