# Поля файла odpm.json

Файл **`odpm.json`** — формальное **описание стека** Odoo-проекта: версии, репозитории, зависимости. Его коммитят в git вместе с модулями, чтобы любой участник команды и машина сборки получили **одинаковый состав**.

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
| `odpm_version` | Версия **формата** этого файла |

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
