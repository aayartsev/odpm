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
| `services.*` / `service_patches.*` (v2) | да — `image`, `user`, `restart`, `hostname`, `pid`, списки (`ports`, `volumes`, `command`, …), значения `environment`, строки в `healthcheck.test` / интервалах; `tty` / `privileged` без подстановки |
| `odoo_conf.*` (v1/v2) | да — все строковые значения во **всех** секциях `odoo_conf` (`options`, `redis_server`, …) |
| `hooks.*` argv (v2) | да — при **выполнении** hook (не при `odpm manifest validate`) |
| `service_sources.*` (v2) | да — значение git-ссылки для каждого имени |

Синтаксис: **`${ИМЯ}`** и **`${ИМЯ:-значение_по_умолчанию}`** (как в Docker Compose). Для sidecar build-контекстов после materialize `service_sources` — **`${@source:<имя>}`** (env-ключ `ODPM_SOURCE_<ИМЯ>`). Для логических имён сервисов compose (`db`, `odoo`, sidecar) — **`${@service:<имя>}`**: в итоговом `docker-compose.yml` подставляется physical имя с учётом `ODPM_COMPOSE_PREFIX` / `POSTGRES_SERVICE_NAME` (например `acme-db`). Для значений из **`.odpm/secrets.json`** — **`${@secret:<ключ>}`** (ключи с точкой, как в schema v1: `partner_armtek.armtek.apilogin`). Подстановка в `services.*.environment` **осознанно** попадает в generated `docker-compose.yml` (файл производный, в git не коммитится); для Odoo-модулей по-прежнему предпочтителен mount `/run/odpm/secrets.json`. Использование `@secret` требует уже существующий `.odpm/secrets.json` или `--secrets-file` в этом запуске (иначе `ConfigError`). Gate при bootstrap смотрит только на **effective** slice активного `ODPM_SCENARIO`, не на другие `scenarios.*`. Заглушки `REPLACE_ME` / `CHANGEME` / `TODO` — ошибка. Литеральный `$` — **`$$`**.

При чтении manifest odpm **не падает** на неразрешённый `${@source:...}` / `${@service:...}` в `services` / `service_patches` (токены сохраняются, пока нет naming/путей); пути `@source` подставляются после materialize, `@service` — из naming `.env` на bootstrap / при повторном expand. Токены `${@secret:...}` при отсутствии файла секретов **не** оставляются — hard fail.

Источник значений (от сильного к слабому): переменные **процесса** (`export`, CI secrets) → ключи из **project `.env`** → default в строке manifest. Отдельный флаг включения **не нужен**.

Пример для команды в git и локальных путей на машине разработчика:

```json
{
  "odoo_git_link": "file://${ODOO_PLATFORM_DIR}",
  "dependencies": [
    "file://${OCA_WEB_PATH}",
    "https://${GIT_HOST}/company/extra.git 19.0"
  ],
  "service_sources": {
    "autoparts_env": "https://${GIT_HOST}/org/autoparts-env.git 17.0"
  }
}
```

В `.env` проекта (или `export` / CI):

```ini
ODOO_PLATFORM_DIR=/home/dev/odoo/19.0
OCA_WEB_PATH=/home/dev/src/oca/web
GIT_HOST=git.company.example
```

Остальные поля (`odoo_version`, `python_version`, `requirements_txt`, …) **без** подстановки. Вложенный `odpm.json` в git-зависимостях поддерживает те же поля — см. [иерархию конфигурации](config-hierarchy.md). В `.odpm/deps.lock.json` попадают **уже раскрытые** URL и пути, не `${VAR}`.

Для v2 sidecar с путями из `.env` и hostname сервисов стека:

```json
"services": {
  "armtek_test": {
    "image": "autoparts_env:emulator",
    "user": "root",
    "tty": true,
    "depends_on": ["db"],
    "environment": {
      "DB_HOST": "${@service:db}",
      "ODOO_URL": "http://${@service:odoo}:8069"
    },
    "volumes": ["${DIGITAL_AUTOPARTS_ENV_DIR}/data:/data:Z"]
  }
}
```

При `ODPM_COMPOSE_PREFIX=acme` в compose попадут `DB_HOST=acme-db` и `ODOO_URL=http://acme-odoo:8069` (синтаксис `depends_on: ["db"]` по-прежнему logical — prefix переписывает список отдельно).

Опционально на sidecar и в `service_patches`: **`hostname`** (строка), **`healthcheck`** (`test` строка или массив строк; `interval` / `timeout` / `retries` / `start_period` / `start_interval` / `disable`), **`privileged`** (boolean) и **`pid`** (строка, напр. `host` или `service:<name>`) — как в Docker Compose; `${VAR}` / `${@service:}` / `${@secret:}` раскрываются в `hostname`, `pid` и строках `healthcheck`.

См. [переменные `.env`](env-dotenv.md), [ссылки на репозитории](git-links.md).

## Блок `service_sources` (git sidecar/build-контексты, 4.7+)

Необязательный объект в **manifest v2** (и в `scenarios.*`) — именованные git-ссылки на внешние репозитории для sidecar-сервисов и `docker build` в hooks. Синтаксис ссылок — как у [`dependencies`](git-links.md) и `platform.git`.

| Поле | Правило |
|------|---------|
| Ключ | `[a-z][a-z0-9_]*` — логическое имя источника |
| Значение | git-ссылка (строка); поддерживается `file://` для локального override |
| `services.<svc>.source` | необязательно; ссылка на имя из effective `service_sources`; при `odpm manifest validate` имя должно существовать |

Пример:

```json
"service_sources": {
  "autoparts_env": "https://github.com/org/autoparts-env.git 17.0"
},
"services": {
  "armtek_test": {
    "source": "autoparts_env",
    "image": "autoparts_env:emulator",
    "volumes": ["${@source:autoparts_env}/data:/data:Z"]
  }
}
```

Правила merge в `scenarios.*`: **`service_sources` — replace-by-name** (overlay перекрывает то же имя, остальные записи сохраняются).

Репозитории из `service_sources` **не** попадают в `dependencies` / `addons_path`. Шаг prepare **`sources.materialize`** (после `git.materialize`) клонирует их в `${ODOO_PROJECTS_DIR}/service-sources/<name>` и подставляет путь через `${@source:<name>}`. Пины коммитов — в `.odpm/deps.lock.json` → `service_sources.<name>` (см. `odpm --update-lock`). Подробнее: [service-sources.md](service-sources.md).

## Блок `odoo_conf` (переопределения Odoo)

Необязательный объект для **командных** настроек Odoo в git (preview, staging, production). Значения из manifest **перекрывают** одноимённые ключи в дисковом `odoo.conf` при сборке `odoo_config_data` для контейнера; обратная запись в `odoo.conf` **не выполняется**.

- **`options`** — секция ядра Odoo (`proxy_mode`, `workers`, …).
- **Другие секции** (`redis_server`, `s3_server`, …) — для модулей/интеграций; merge по имени секции, как в INI. Значения — строки (числа/bool в JSON приводятся к строке). В значениях работают `${VAR}`, `${@service:…}`, `${@secret:…}`.

```json
"odoo_conf": {
  "options": {
    "proxy_mode": "True",
    "dbfilter": "^${PREVIEW_HOSTNAME}$",
    "workers": "2",
    "log_level": "debug"
  },
  "redis_server": {
    "host": "${@service:redis}",
    "port": "6379",
    "password": "${@secret:redis_password}"
  },
  "s3_server": {
    "endpoint": "${@service:minio}:9000",
    "secret_key": "${@secret:minio_root_password}"
  }
}
```

На `odpm manifest validate` в **`options`** нельзя указывать ключи, которыми управляет odpm: `addons_path`, `data_dir`, `db_host`, `db_port`, `db_user`, `db_password`, `admin_passwd`, `http_port`. Подробнее: [odoo.conf](odoo-conf.md).

## Блок `secrets` (обязательные локальные секреты, 4.7)

Необязательный объект в **manifest v2** (и в `scenarios.*`) — декларация, что проекту нужен `.odpm/secrets.json` до подъёма стека:

```json
"secrets": {
  "required": true,
  "keys": ["payment_provider.api_key", "armtek.api_token"]
}
```

| Поле | Назначение |
|------|------------|
| `required` | `true` — для сценариев с host-mount секретов (`developer`, `server`) odpm проверяет наличие `.odpm/secrets.json` **до** `docker compose up` |
| `keys` | Необязательный список ключей для **строгой** проверки содержимого; без `keys` достаточно существования файла (в сообщении об ошибке ключи из `secrets.example.json` — только подсказка) |
| `provider` | Необязательный источник: `type` (`file` / `infisical` / id плагина) и поля Infisical (`host`, `project_id` **или** `project_slug`, `environment_slug`, `secret_path`, `recursive`, `key_map`). Overlay `scenarios.*.secrets.provider` **заменяет** весь объект, не мержит поля. См. [ADR-021](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-021-secrets-providers.md). |

Проверки (без вывода значений):

- **`odpm manifest validate`** — предупреждение, если секреты не удовлетворены;
- **`odpm plan`** — warning в списке предупреждений;
- **`odpm`** (без `--skip-start`) — ошибка до `pre_up` / compose, если файл отсутствует, ключи не заполнены или остались placeholder (`REPLACE_ME`).

Пример Infisical (credentials только в `.env` / process env):

```json
"secrets": {
  "required": true,
  "keys": ["payment_provider.api_key"],
  "provider": {
    "type": "infisical",
    "host": "https://app.infisical.com",
    "project_id": "…",
    "environment_slug": "dev",
    "secret_path": "/odoo",
    "key_map": {
      "PAYMENT_API_KEY": "payment_provider.api_key"
    }
  }
}
```

В сценарии **`ci`** host-mount отключён — проверка `required` не выполняется; overlay может задать `"secrets": { "required": false }`. Подробнее: [secrets.md](../operations/secrets.md).

## Блок `scenarios` (overlays по `ODPM_SCENARIO`, 4.7)

Необязательный объект в **manifest v2** для переопределения `odoo_conf`, `services`, `service_patches`, `service_sources`, `requirements`, `dependencies`, `hooks` и `secrets` **по сценарию** из project `.env` (`ODPM_SCENARIO`: `developer`, `server`, `ci`). Один `odpm.json` в git — разные effective-настройки на ноутбуке, сервере и CI без `${VAR}`-обходов.

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
| `service_sources` | replace-by-name (overlay перекрывает то же имя) |
| `requirements` | concat + dedupe |
| `dependencies` | concat + dedupe (git-репозитории) |
| `hooks` | append по фазам (`post_clone`, `post_prepare`, `pre_up`); корень, затем overlay |
| `secrets` | `required` — overlay переопределяет, если задан; `keys` — concat + dedupe для строгой проверки; `provider` — **полная замена** объекта (как `services` по имени), не merge полей |

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
