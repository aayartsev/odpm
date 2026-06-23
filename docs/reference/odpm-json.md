# Поля файла odpm.json

Файл **`odpm.json`** — формальное **описание стека** Odoo-проекта: версии, репозитории, зависимости. Его коммитят в git вместе с модулями, чтобы любой участник команды и машина сборки получили **одинаковый состав**.

| Поле | Назначение |
|------|------------|
| `python_version` | Версия Python в контейнере, напр. `"3.10"` |
| `distro_name` | Семейство Linux (сейчас поддерживается `"debian"`) |
| `distro_version` | Версия дистрибутива: `"11"`, `"12"`, `"bullseye"` |
| `postgres_version` | Версия PostgreSQL в compose, напр. `"15"` |
| `odoo_version` | Версия Odoo: `"19.0"`, `"18.0"` |
| `dependencies` | Список git-ссылок на репозитории дополнений |
| `requirements_txt` | Список строк как в requirements.txt |
| `odoo_git_link` | Репозиторий **платформы**; ветка/коммит через пробел |
| `platform_name` | Имя Python-пакета форка (по умолчанию `"odoo"`) |
| `odoo_build_date` | Дата ночной сборки `ГГГГММДД` или `"latest"` |
| `odpm_version` | Версия **формата** этого файла |

## Подстановка `${VAR}` в строковых полях

В **whitelist-полях** odpm раскрывает ссылки на переменные окружения сразу после чтения JSON:

| Поле | Подстановка |
|------|-------------|
| `odoo_git_link` | да |
| `dependencies` | да (каждый элемент списка) |
| `services.*` / `service_patches.*` (v2) | да — `image`, `user`, `restart`, списки (`ports`, `volumes`, `command`, …), значения `environment` |
| `hooks.*` argv (v2) | да — при **выполнении** hook (не при `odpm manifest validate`) |

Синтаксис: **`${ИМЯ}`** и **`${ИМЯ:-значение_по_умолчанию}`** (как в Docker Compose). Литеральный `$` — **`$$`**.

Источник значений (от сильного к слабому): переменные **процесса** (`export`, CI secrets) → ключи из **project `.env`** → default в строке manifest. Отдельный флаг включения **не нужен**.

Пример для команды в git и локальных путей на машине разработчика:

```json
{
  "odoo_git_link": "file://${ODOO_PLATFORM_DIR}",
  "dependencies": [
    "file://${OCA_WEB_PATH}",
    "https://${GIT_HOST}/company/extra.git 19.0"
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

Для v2 sidecar с путями из `.env`:

```json
"services": {
  "armtek_test": {
    "image": "autoparts_env:emulator",
    "user": "root",
    "tty": true,
    "volumes": ["${DIGITAL_AUTOPARTS_ENV_DIR}/data:/data:Z"]
  }
}
```

См. [переменные `.env`](env-dotenv.md), [ссылки на репозитории](git-links.md).

## Проверенные сочетания

- **Debian 11:** Python 3.7, 3.10 — Odoo 11–16.
- **Debian 12:** Python 3.10 — Odoo 16–19.
- **Debian 13:** Python 3.10, 3.12.

См. [свой репозиторий платформы](../scenarios/platform-fork.md), [ссылки на репозитории](git-links.md).
