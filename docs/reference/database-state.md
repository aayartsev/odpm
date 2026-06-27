# Состояние PostgreSQL и drift

Начиная с odpm 4.3, конфигурация **кластера PostgreSQL** (compose, `odoo.conf`, data dir, роль приложения) отслеживается через снимок **`.odpm/database/last_run.json`**. Это отдельный слой от операций с **Odoo-базами** (`-d`, `--db-backup`, `--db-restore`).

## Зачем это нужно

Раньше «правда» о базе была размазана по `.env`, `docker-compose.yml`, `odoo.conf`, bind mount data dir и фактическому содержимому PostgreSQL. После переименования сервиса, смены порта или подключения к старому data dir ошибки проявлялись глубоко внутри контейнера.

Теперь odpm:

1. Собирает **fingerprints** текущей конфигурации.
2. Сравнивает их с последним снимком (`last_run.json`).
3. Показывает **drift** в `odpm plan` и перед запуском контейнеров.
4. На первом запуске **настраивает** legacy-проекты без снимка (adoption baseline).

## Файл `.odpm/database/last_run.json`

| Свойство | Значение |
|----------|----------|
| Генерация | odpm автоматически |
| Git | **не коммитить** (как `runtime/config.json`) |
| Mount в контейнер | `.odpm/database` → `/run/odpm/database` (read-write для checker) |
| `schema_version` | `1` |

Снимок содержит:

- **`compose`** — имя сервиса PostgreSQL, тег образа, абсолютный путь data dir, порт на хосте; при `ODPM_COMPOSE_PREFIX` — также `compose_project_name` и `odoo_service_name`;
- **`odoo_conf`** — `db_host`, `db_port`, `db_user`;
- **`cluster`** — data dir непустой, major PostgreSQL (`PG_VERSION`), роль приложения и её наличие.

## Когда обновляется baseline

| Событие | Кто записывает |
|---------|----------------|
| Первый запуск без `last_run.json` | **Adoption** — до `compose up` (роль + baseline) |
| Успешная проверка credentials в checker | **Checker** — после TCP и `psql` от имени `db_user` |

Adoption срабатывает **один раз**. Пока файл есть, повторной «настройки» не будет — только drift относительно сохранённого снимка.

## Adoption legacy-проектов

Если в каталоге проекта ещё нет `last_run.json` (типично: унаследованный data dir PostgreSQL), перед полным стеком odpm:

1. Поднимает сервис PostgreSQL (если не готов).
2. Выполняет **`ensure_app_role`** — создаёт или обновляет роль приложения (`odoo` по умолчанию), в том числе через single-user bootstrap, если в кластере нет административной login-роли.
3. Записывает текущую конфигурацию как baseline.

**Adoption не делает:**

- смену владельца (owner) существующих Odoo-баз в PostgreSQL;
- удаление или восстановление Odoo-баз;
- автоматический wipe data dir при смене major PostgreSQL.

Подробнее для унаследованных проектов: [legacy-project.md](../getting-started/legacy-project.md).

## Drift: виды и серьёзность

| KIND | Severity | Поведение |
|------|----------|-----------|
| `first_run` | info | Нет снимка; baseline будет принят при старте |
| `service_name`, `db_host_mismatch`, `host_port` | low | Предупреждение в plan |
| `odpm_scenario`, `data_dir_empty_changed` | medium | Интерактивный prompt или `--accept-database-drift` |
| `data_path`, `postgres_major`, `app_role_missing` | high | Prompt; без resolve **блокирует** старт контейнеров |

Шаг подготовки **`database.drift`** в `odpm plan` отражает расхождения до записи compose.

### Интерактивное разрешение

При подключённом TTY odpm задаёт вопросы (принять новый data path, создать роль, показать инструкции wipe и т.д.). Без TTY — ошибка с перечислением KIND; используйте **`--accept-database-drift=KIND`** (флаг можно повторять).

Допустимые KIND для `--accept-database-drift`:

- `data_path`
- `postgres_major`
- `app_role_missing`
- `odpm_scenario`
- `data_dir_empty_changed`

См. [запуск без диалогов](../operations/non-interactive.md).

## Подкоманда `database`

```bash
odpm database status
odpm database status --format json
odpm database ensure-role
```

| Команда | Назначение |
|---------|------------|
| `database status` | Fingerprints, drift, live-probe (контейнер postgres, готовность, роль) |
| `database status --format json` | То же в JSON для скриптов |
| `database ensure-role` | Создать или обновить роль приложения в **запущенном** PostgreSQL |

Команды выполняют prepare (без `compose up`), если это нужно для чтения конфигурации.

## Связь с `.env` и `odoo.conf`

Переменная **`POSTGRES_SERVICE_NAME`** в `.env` задаёт имя сервиса postgres в `docker-compose.yml` и ожидаемый **`db_host`** в `odoo.conf`, когда **`ODPM_COMPOSE_PREFIX`** не задан.

Переменная **`ODPM_COMPOSE_PREFIX`** задаёт **физические** имена встроенных сервисов (`{prefix}db`, `{prefix}odoo`), том данных и имя проекта Docker Compose. В снимке `last_run.json` сохраняются `compose.service_name` (postgres), `compose.compose_project_name` и `compose.odoo_service_name`. При смене префикса или `POSTGRES_SERVICE_NAME` относительно снимка:

- шаг **`template.odoo_conf`** пересоздаёт конфиг при рассинхроне `db_host`;
- drift **`service_name`**, **`compose_project_name`** или **`db_host_mismatch`** попадает в plan.

Подробнее: [переменные .env](env-dotenv.md), [odoo.conf](odoo-conf.md).

## Odoo-базы: backup, restore, drop

Операции **`--db-drop`**, **`--db-restore`**, **`--db-backup`** работают на уровне **Odoo-баз** внутри кластера, а не на уровне `last_run.json`.

На legacy-кластере база может существовать, но быть **владельцем другого PostgreSQL-пользователя**. Тогда стандартный Odoo `exp_drop` молча пропускает удаление; odpm выполняет прямой `DROP DATABASE` и выдаёт ошибку, если база осталась.

Пример полного цикла:

```bash
odpm -d test_db --db-drop --db-restore my_backup.zip -i -u --set-admin-pass
```

## Диагностика

```bash
odpm database status
odpm plan --skip-start
docker compose logs db-dev    # имя postgres-сервиса из .env (или acme-db при ODPM_COMPOSE_PREFIX=acme)
```

После смены `POSTGRES_SERVICE_NAME` или `ODPM_COMPOSE_PREFIX` удалите orphan-контейнеры (с тем же project scope, что у odpm):

```bash
docker compose down --remove-orphans
# при префиксе odpm передаёт -p автоматически; вручную: docker compose -p acme down --remove-orphans
```

## Что odpm не автоматизирует

- Миграцию данных при смене major PostgreSQL (нужен backup и wipe data dir по инструкции в prompt).
- `ALTER DATABASE … OWNER TO` для старых Odoo-баз — только явные операции (`--db-drop`, ручной `psql`).
- Синхронизацию `last_run.json` между машинами — снимок **локальный** для каждого каталога окружения.
