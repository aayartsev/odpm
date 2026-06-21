# Поля файла odpm.json

Файл **`odpm.json`** — формальное **описание стека** Odoo-проекта: версии, репозитории, зависимости. Его коммитят в git вместе с модулями, чтобы любой участник команды и машина сборки получили **одинаковый состав**.

odpm 4.4 поддерживает два формата:

| Формат | Маркер | Когда использовать |
|--------|--------|-------------------|
| **v1 flat** (по умолчанию) | `odpm_version: "4.0"`, без `manifest_schema` | Существующие проекты, без изменений |
| **v2 nested** | `manifest_schema: 2`, `requires_odpm: "4.4.2"` | `services`, `hooks`, `locks` в манифесте |

Миграция: **`odpm manifest migrate`** — см. [manifest-migration.md](manifest-migration.md).

## Flat v1 (поля верхнего уровня)

| Поле | Назначение |
|------|------------|
| `python_version` | Версия Python в контейнере, напр. `"3.10"` |
| `distro_name` | Семейство Linux (сейчас поддерживается `"debian"`) |
| `distro_version` | Версия дистрибутива: `"11"`, `"12"`, `"bullseye"` |
| `postgres_version` | Версия PostgreSQL в compose, напр. `"15"` |
| `odoo_version` | Версия Odoo: `"17.0"`, `"16.0"` |
| `dependencies` | Список git-ссылок на репозитории дополнений |
| `requirements_txt` | Список строк как в requirements.txt |
| `odoo_git_link` | Репозиторий **платформы**; ветка/коммит через пробел |
| `platform_name` | Имя Python-пакета форка (по умолчанию `"odoo"`) |
| `odoo_build_date` | Дата ночной сборки `ГГГГММДД` или `"latest"` |
| `odpm_version` | **Контрактная строка формата** v1 (`"4.0"`), не версия менеджера |

## Оси версий (manager vs manifest)

У **продукта** одна версия; в **манифесте** — отдельные поля формата:

| Константа / поле | Пример | Назначение |
|------------------|--------|------------|
| `RELEASE_VERSION` / `ODPM_VERSION` | `"4.4.2"` | Версия **установленного менеджера** (`odpm --version`, pip, deb/rpm) |
| `MANIFEST_V1_CONTRACT_LINE` | `"4.0"` | Строка `odpm_version`, которую odpm **пишет в новые** flat-проекты |
| `DEFAULT_ODPM_VERSION` | `"3.0"` | **Legacy fallback**, если поле `odpm_version` **отсутствует** в flat v1 |

Поведение compat (`dev_project/manifest/compat.py`):

- Flat v1 **без** `manifest_schema` и **без** `odpm_version` → контракт считается `"3.0"` (поддерживается manager 4.4.2).
- Новые проекты и миграции → `odpm_version: "4.0"`.
- v2 nested → `requires_odpm` (минимальная semver-версия менеджера; новые проекты получают текущий `RELEASE_VERSION`), не `odpm_version`.

Проверка без bootstrap: **`odpm manifest validate`** (JSON Schema v1 или v2 + compat-check).

## Nested v2 (дополнительные блоки)

Обязательные поля v2: `manifest_schema`, `requires_odpm`, `platform`, `python`, `distro`, `postgres`.

| Блок / поле | Назначение |
|-------------|------------|
| `manifest_schema` | `2` |
| `requires_odpm` | Минимальная версия odpm, напр. `"4.4.2"` |
| `platform.git` | Аналог `odoo_git_link` |
| `platform.build_date` | Аналог `odoo_build_date` |
| `python` | Аналог `python_version` |
| `distro.name` / `distro.version` | Аналог `distro_name` / `distro_version` |
| `postgres` | Аналог `postgres_version` |
| `requirements` | Аналог `requirements_txt` |
| `developing.git` | URI разрабатываемого проекта |
| `locks.git` | Декларативные git SHA (синхрон с `.odpm/deps.lock.json`) |
| `locks.venv` | Хеш venv lock (опционально) |
| `hooks.post_prepare` | Shell argv или plugin id после prepare |
| `hooks.pre_up` | Shell argv или plugin id перед `docker compose up` |
| `services.<name>` | Дополнительные compose-сервисы: обязателен `image`; опционально `ports[]`, `environment`, `volumes[]`, `depends_on[]`, `restart` |

Пример Mailpit: [plugins.md](plugins.md).

Валидация: **`odpm manifest validate`** (JSON Schema v1/v2 на host, read-only). При bootstrap v1 проходит compat-check без jsonschema; v2 — jsonschema в `load_manifest`.

## Блок `database` (язык и страна новой базы)

Опциональный объект для **командной** идентичности проекта при первом создании базы (`-d`):

| Поле | Назначение |
|------|------------|
| `database.language` | Язык базы Odoo, напр. `ru_RU`, `en_US` |
| `database.country` | Код страны (`RU`, `US`) или `false` / `null` |

Значения из манифеста **перекрывают** одноимённые поля в `user_settings.json` → `db_creation_data`. Локальные параметры создания базы (`create_demo`, логин/пароль администратора) остаются в [user_settings.json](user-settings.md).

Пример (v1 flat или v2):

```json
"database": {
  "language": "ru_RU",
  "country": "RU"
}
```

## Миграция v1 → v2

Команда **`odpm manifest migrate`** показывает unified diff преобразования flat-манифеста в nested v2. С флагом **`--write`** записывает результат в `odpm.json` разрабатываемого проекта. Подробнее: [manifest-migration.md](manifest-migration.md).

При миграции odpm переносит:

| Источник | Куда в v2 |
|----------|-----------|
| flat-поля (`python_version`, `odoo_git_link`, …) | `python`, `platform`, `distro`, … |
| `database` в манифесте или `db_creation_data` в `user_settings.json` | `database` |
| `developing_project` в `user_settings.json` | `developing.git` |
| `.odpm/deps.lock.json` | `locks.git` |

После миграции v1 flat по-прежнему читается менеджером 4.4 до переключения файла. Проекты без миграции не ломаются.

## Подстановка `${VAR}` в строковых полях

В **whitelist-полях** odpm раскрывает ссылки на переменные окружения сразу после чтения JSON:

| Поле | Подстановка |
|------|-------------|
| `odoo_git_link` | да |
| `dependencies` | да (каждый элемент списка) |

Синтаксис: **`${ИМЯ}`** и **`${ИМЯ:-значение_по_умолчанию}`** (как в Docker Compose). Литеральный `$` — **`$$`**.

Источник значений (от сильного к слабому): переменные **процесса** (`export`, CI secrets) → ключи из **project `.env`** → default в строке manifest. Отдельный флаг включения **не нужен**.

Пример для команды в git и локальных путей на машине разработчика:

```json
{
  "odoo_git_link": "file://${ODOO_PLATFORM_DIR}",
  "dependencies": [
    "file://${OCA_WEB_PATH}",
    "https://${GIT_HOST}/company/extra.git 17.0"
  ]
}
```

В `.env` проекта (или `export` / CI):

```ini
ODOO_PLATFORM_DIR=/home/dev/odoo/19.0
OCA_WEB_PATH=/home/dev/src/oca/web
GIT_HOST=git.company.example
```

Остальные поля (`odoo_version`, `python_version`, `requirements_txt`, …) **без** подстановки. Вложенный `odpm.json` в git-зависимостях поддерживает те же поля — см. [иерархию конфигурации](config-hierarchy.md). В `.odpm/deps.lock.json` попадают **уже раскрытые** URL и пути, не `${VAR}`.

См. [переменные `.env`](env-dotenv.md), [ссылки на репозитории](git-links.md).

## Проверенные сочетания

- **Debian 11:** Python 3.7, 3.10 — Odoo 11–16.
- **Debian 12:** Python 3.10 — Odoo 16–17.
- **Debian 13:** Python 3.10, 3.12.

См. [свой репозиторий платформы](../scenarios/platform-fork.md), [ссылки на репозитории](git-links.md).
