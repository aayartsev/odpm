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
| `odoo_conf.*` (v1/v2) | да — все строковые значения в `odoo_conf.options` |
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

## Блок `odoo_conf` (переопределения Odoo)

Необязательный объект для **командных** настроек Odoo в git (preview, staging, production). Значения из manifest **перекрывают** одноимённые ключи в дисковом `odoo.conf` при сборке `odoo_config_data` для контейнера; обратная запись в `odoo.conf` **не выполняется**.

```json
"odoo_conf": {
  "options": {
    "proxy_mode": "True",
    "dbfilter": "^${PREVIEW_HOSTNAME}$",
    "workers": "2",
    "log_level": "debug"
  }
}
```

На `odpm manifest validate` нельзя указывать ключи, которыми управляет odpm: `addons_path`, `data_dir`, `db_host`, `db_port`, `db_user`, `db_password`, `admin_passwd`, `http_port`. Подробнее: [odoo.conf](odoo-conf.md).

## Блок `scenarios` (overlays по `ODPM_SCENARIO`, 4.7)

Необязательный объект в **manifest v2** для переопределения `odoo_conf`, `services`, `service_patches`, `requirements`, `dependencies` и `hooks` **по сценарию** из project `.env` (`ODPM_SCENARIO`: `developer`, `server`, `ci`). Один `odpm.json` в git — разные effective-настройки на ноутбуке, сервере и CI без `${VAR}`-обходов.

| Режим | Условие | Effective slice |
|-------|---------|-----------------|
| **Legacy** | ключа `scenarios` **нет** | только top-level поля |
| **Multi** | `scenarios` **есть** (даже `{}`) | top-level **+** overlay `scenarios[ODPM_SCENARIO]` |

Правила merge:

| Поле | Merge |
|------|-------|
| `odoo_conf` | deep merge по секциям |
| `services` | overlay заменяет сервис по имени |
| `service_patches` | merge по [ADR-009](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-009-compose-service-patch.md) |
| `requirements` | concat + dedupe |
| `dependencies` | concat + dedupe (git-репозитории) |
| `hooks` | append по фазам (`post_clone`, `post_prepare`, `pre_up`); корень, затем overlay |

Manifest со `scenarios` рекомендуется с **`requires_odpm: "4.7.0"`**. v1 + `scenarios` → ошибка validate. Подробнее: [ADR-011](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-011-scenario-manifest-overrides.md).

Пример: на сервере больше workers, в developer — sidecar mailpit:

```json
{
  "manifest_schema": 2,
  "requires_odpm": "4.7.0",
  "odoo_conf": { "options": { "proxy_mode": "True", "workers": "0" } },
  "services": {
    "mailpit": { "image": "axllent/mailpit", "depends_on": ["db"] }
  },
  "scenarios": {
    "server": {
      "odoo_conf": { "options": { "workers": "4" } },
      "services": {}
    },
    "developer": {
      "requirements": ["ipython"],
      "dependencies": ["https://github.com/my-org/test-fixtures.git 17.0"],
      "hooks": {
        "post_prepare": [["docker", "build", "-t", "autoparts_env:emulator", "."]]
      }
    }
  }
}
```

В manifest и плагинах для sidecar используйте **логические** имена `depends_on: ["db"]`; при `ODPM_COMPOSE_PREFIX` в `.env` odpm перепишет их в physical — см. [env-dotenv.md](env-dotenv.md).

## Проверенные сочетания

- **Debian 11:** Python 3.7, 3.10 — Odoo 11–16.
- **Debian 12:** Python 3.10 — Odoo 16–19.
- **Debian 13:** Python 3.10, 3.12.

См. [свой репозиторий платформы](../scenarios/platform-fork.md), [ссылки на репозитории](git-links.md).
