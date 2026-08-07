# Плагины и расширения odpm (4.4+)

odpm 4.4+ добавляет **extension API** на host: prepare steps, compose fragments и lifecycle hooks. Плагины не получают прямой доступ к mutable `Config` — только frozen [`ExtensionHostContext`](https://github.com/aayartsev/odpm/blob/4.4-dev/dev_project/extensions/context.py).

## Версия API (4.6+)

Текущая версия extension API: **`EXTENSION_API_VERSION = "1.1"`** (`dev_project/extensions/api.py`). Поддерживаются **1.0** и **1.1**; модули без `EXTENSION_API_VERSION` считаются **1.0**. Host проверяет версию при загрузке entry points и `.odpm/plugins/*.py`. В плагине:

```python
from dev_project.extensions.api import EXTENSION_API_VERSION, assert_extension_api_compatible

assert_extension_api_compatible(EXTENSION_API_VERSION)
```

Breaking changes в протоколах pluggy или manifest hooks требуют major bump API. Политика: [ADR-004](https://github.com/aayartsev/odpm/blob/4.6.0-dev/docs/contributing/adr-004-plugin-api-stability.md).

## Три способа расширить проект

| Механизм | Где объявляется | Когда выполняется |
|----------|-----------------|-------------------|
| **Manifest `services`** | `odpm.json` v2 → `services` | Prepare `compose.fragments` + `odpm plan` → `compose.fragment.<name>` |
| **Manifest `hooks`** | `odpm.json` v2 → `hooks` | `post_clone` после git materialize; `post_prepare` после prepare; `pre_up` перед compose up |
| **Python entry points** | `pyproject.toml` пакета | Pluggy: `odpm.prepare_steps`, `odpm.hooks` |
| **Project-local plugins** | `.odpm/plugins/*.py` или `extensions.local` | Импорт при bootstrap (только внутри `project_dir`) |

Подробнее о полях v2: [odpm.json](odpm-json.md). ADR: [adr-001-extensions-and-manifest-v2.md](https://github.com/aayartsev/odpm/blob/4.6.0-dev/docs/contributing/adr-001-extensions-and-manifest-v2.md).

## Декларативный сервис (Mailpit)

Тестовый SMTP с веб-интерфейсом на порту **8025**. Добавьте в nested manifest v2:

```json
{
  "manifest_schema": 2,
  "requires_odpm": "4.6.0",
  "services": {
    "mailpit": {
      "image": "axllent/mailpit",
      "restart": "unless-stopped",
      "ports": ["8025:8025", "1025:1025"]
    }
  }
}
```

Для sidecar доступны также **`user`**, **`tty`**, **`hostname`**, **`healthcheck`** (как в `service_patches`). Для sidecar с **git build-контекстом** (рекомендуется, 4.7+) используйте `service_sources` и `${@source:...}`; для API-ключей sidecar — `${@secret:...}` из `.odpm/secrets.json`:

```json
"service_sources": {
  "autoparts_env": "https://github.com/org/autoparts-env.git 17.0"
},
"services": {
  "armtek_test": {
    "source": "autoparts_env",
    "image": "autoparts_env:emulator",
    "user": "root",
    "tty": true,
    "volumes": ["${@source:autoparts_env}/data:/data:Z"],
    "environment": {
      "APILOGIN": "${@secret:partner_armtek.armtek.apilogin}"
    }
  }
},
"hooks": {
  "post_prepare": [
    [
      "docker", "build",
      "-f", "${@source:autoparts_env}/Dockerfile",
      "-t", "autoparts_env:emulator",
      "${@source:autoparts_env}"
    ]
  ]
}
```

`${@secret:...}` требует `.odpm/secrets.json` или `--secrets-file`; значение попадёт в generated compose YAML (осознанно). Подробнее: [secrets.md](../operations/secrets.md).

См. [service-sources.md](service-sources.md). Legacy-вариант с путём из `.env`:

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

Тот же spec в коде: `dev_project.extensions.reference.mailpit.MAILPIT_SERVICE_SPEC`.

После `odpm up` сервис появится в сгенерированном `docker-compose.yml` (блок `{COMPOSE_SERVICE_FRAGMENTS}`). Артефакты materialize: `.odpm/compose/fragments/mailpit.yml` (gitignored).

В `depends_on` sidecar указывайте **логическое** имя `db` (не physical `acme-db`); при `ODPM_COMPOSE_PREFIX` odpm перепишет зависимости при генерации compose — см. [env-dotenv.md](env-dotenv.md).

### Compose-сеть (`networks`, 4.7+)

По умолчанию весь стек живёт в implicit default network Docker Compose. Чтобы объявить **одну** именованную сеть для всех сервисов, задайте в `.env`:

```ini
ODPM_COMPOSE_NETWORK=stack
```

Для **external** сети reverse proxy (Traefik, Caddy) — обычно в `~/.odpm/.env`:

```ini
ODPM_COMPOSE_NETWORK=proxy
ODPM_COMPOSE_NETWORK_EXTERNAL=1
```

См. [env-dotenv.md](env-dotenv.md), [ADR-014](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-014-compose-stack-network.md).

В manifest sidecar можно указать `networks` (логические имена; при `ODPM_COMPOSE_PREFIX` odpm перепишет managed-сеть в physical, external — без prefix):

```json
"services": {
  "metrics": {
    "image": "prom/prometheus",
    "networks": ["stack"]
  }
}
```

Если в manifest указано `networks: ["stack"]`, в `.env` должно быть **`ODPM_COMPOSE_NETWORK=stack`** (или уберите `networks` — odpm подключит sidecar автоматически). `odpm manifest validate` выдаёт **warning**, если логическое имя `stack` не совпадает с `.env`.

Для proxy-only sidecar без odpm-managed `stack`:

```json
"networks": ["${PROXY_NETWORK}"]
```

с `PROXY_NETWORK=proxy` и `ODPM_COMPOSE_NETWORK=proxy` в `.env`.

### Patch built-in сервисов (`service_patches`, 4.6+)

Имена **`odoo`**, **`db`**, **`postgres`** нельзя объявлять в `services` — только patch. Политика: [ADR-009](https://github.com/aayartsev/odpm/blob/4.6.0-dev/docs/contributing/adr-009-compose-service-patch.md).

```json
"service_patches": {
  "odoo": {
    "environment": {
      "CUSTOM_METRIC": "1"
    }
  }
}
```

`odpm plan` показывает `compose.patch.odoo` (preview); patch применяется при `compose.generate`.

### `command` / `entrypoint` для sidecar (4.6+)

Только **exec form** (JSON-массив строк) в `services.<name>`:

```json
"services": {
  "worker": {
    "image": "busybox:latest",
    "command": ["sh", "-c", "sleep infinity"]
  }
}
```

Команда `odoo` по-прежнему задаётся generator; override — через `service_patches.odoo.command` при явной необходимости.

## Lifecycle hooks в manifest

```json
"hooks": {
  "post_prepare": [
    ["./scripts/notify.sh", "prepare-done"],
    "mycompany.odpm.hooks.warmup"
  ],
  "pre_up": [
    ["docker", "network", "create", "odpm-dev", "||", "true"]
  ]
}
```

Каждый элемент — либо **argv** (массив строк, выполняется в `project_dir` **без shell**), либо **plugin id** (строка) для pluggy hook runner.

В argv поддерживается **`${VAR}`** / **`${VAR:-default}`**, **`${@source:<name>}`** (после `sources.materialize`) и **`${@secret:<key>}`** (из `.odpm/secrets.json`): раскрытие при выполнении hook. Subprocess получает **merged env** (process + недостающие ключи из `.env`).

```json
"hooks": {
  "post_prepare": [[
    "docker", "build",
    "-f", "${@source:autoparts_env}/Dockerfile",
    "-t", "autoparts_env:emulator",
    "${@source:autoparts_env}"
  ]]
}
```

В `services` / `service_patches` те же правила подстановки для строковых полей (`image`, `volumes[]`, `command[]`, `environment`, …) — `${VAR}` / `${@secret:...}` при чтении manifest; `${@source:...}` после `sources.materialize`.

Порядок prepare (фрагмент):

1. Git materialize
2. **`sources.materialize`** (если есть `service_sources`)
3. `hooks.post_clone` (если задан)
4. Все prepare steps (built-in + `odpm.prepare_steps` + local plugins), сортировка по `order`
5. `hooks.post_prepare`
6. Runtime: debug profile, IDE, database drift
6. `hooks.pre_up`
7. `docker compose up`

`odpm plan` показывает шаги `hooks.*`, `compose.fragment.<service>` и `compose.patch.<service>` когда они настроены.

### Поле `order` у prepare steps

Меньшее значение `order` выполняется раньше среди **extension** steps (built-in порядок фиксирован в registry). Конфликт `id` с built-in step → `ValueError` при регистрации.

Ошибка shell-hook → `PipelineError` с кодом выхода команды.

## Python-плагин: compose fragment

```python
# my_odpm_mailpit/__init__.py
from dev_project.extensions import ExtensionHostContext, register_compose_fragment
from dev_project.extensions.reference.mailpit import MAILPIT_SERVICE_SPEC

class MailpitFragment:
    name = "mailpit"

    def compose_services(self, ctx: ExtensionHostContext) -> dict:
        return {"mailpit": dict(MAILPIT_SERVICE_SPEC)}

def _register():
    register_compose_fragment("mailpit", MailpitFragment())
```

Регистрация при импорте пакета или через entry point (см. ниже).

### Patch built-in из Python (API 1.1+)

Опциональный метод `compose_service_patches` на compose fragment (те же правила, что manifest `service_patches`):

```python
def compose_service_patches(self, ctx: ExtensionHostContext) -> dict:
    return {"odoo": {"environment": {"MY_FLAG": "1"}}}
```

### Nested dependency `services` (4.6+)

При `use_oca_dependencies` v2 `services` / `service_patches` из `odpm.json` зависимостей наследуются в host compose после `project.map_folders`. При конфликте имён **побеждает host manifest**. См. [ADR-004](https://github.com/aayartsev/odpm/blob/4.6.0-dev/docs/contributing/adr-004-plugin-api-stability.md).

## Python-плагин: prepare step

```toml
[project.entry-points."odpm.prepare_steps"]
my_step = "my_odpm_plugin.steps:plugin_factory"
```

```python
from dataclasses import dataclass
from dev_project.prepare.helpers import make_plan_step
from dev_project.prepare.types import PrepareContext

@dataclass(frozen=True)
class MyPrepareStep:
    id: str = "mycompany.custom.step"
    description: str = "Custom prepare work"
    order: int = 500

    def evaluate(self, ctx: PrepareContext):
        return make_plan_step(self.id, self.description, "run", True, "always run")

    def execute(self, ctx: PrepareContext) -> None:
        ...

def plugin_factory():
    return MyPrepareStep()
```

`evaluate` должен быть **без side effects** — `odpm plan` вызывает только evaluate.

## Python-плагин: lifecycle hook runner

```toml
[project.entry-points."odpm.hooks"]
warmup = "my_odpm_plugin.hooks:WarmupRunner"
```

```python
class WarmupRunner:
    name = "mycompany.odpm.hooks.warmup"

    def run_post_clone(self, ctx) -> None:
        ...

    def run_post_prepare(self, ctx) -> None:
        ...

    def run_pre_up(self, ctx) -> None:
        ...
```

Id в manifest (`"mycompany.odpm.hooks.warmup"`) должен совпадать с `name` runner.

## Пример `pyproject.toml` пакета

```toml
[project]
name = "odpm-services-mailpit"
version = "0.1.0"
dependencies = ["odpm>=4.4"]

[project.entry-points."odpm.hooks"]
# optional lifecycle runners

[project.entry-points."odpm.prepare_steps"]
# optional prepare steps
```

Установите пакет в venv host (`pip install -e .`) рядом с odpm.

## Project-local plugins (4.5+)

Без отдельного pip-пакета можно положить модули в **`.odpm/plugins/`** проекта (только этот каталог, без `..` в именах). Опциональный allow-list в manifest v2:

```json
"extensions": {
  "local": ["mailpit_local"]
}
```

Загружается `project_dir/.odpm/plugins/mailpit_local.py`. Пример fixture: `tests/fixtures/sample_plugin/`.

## Cookbook (минимальный плагин)

1. Manifest v2 `services.mailpit` **или** `register_compose_fragment` в Python.
2. Prepare step с `evaluate` без side effects + `execute` для записи файлов.
3. Hook runner с `name`, совпадающим с id в `hooks.post_prepare`.
4. `pip install -e .` или `.odpm/plugins/my_plugin.py`.
5. `odpm plan` — проверить шаги `compose.fragment.*`, `hooks.*`, extension prepare step.

Шаблон `pyproject.toml`: `tests/fixtures/sample_plugin/pyproject.toml`.

## Ограничения

- Container-side `ContainerConfig` остаётся **stdlib-only** (без новых PyPI deps в образе).
- Compose YAML генерируется host-движком `dev_project/yaml/` (ruamel.yaml); YAML anchors/merge aliases не поддерживаются.
- Конфликт имён: plugin compose fragment **перезаписывает** одноимённый service из manifest.

## См. также

- [Сгенерированные файлы](generated-files.md) — `.odpm/compose/fragments/`
- Declarative sidecar-сервисы — секция **Mailpit** выше и таблица механизмов расширения
- Устаревшие черновики в `dev_project/plugins/` (`services_ru.md`, `todo_ru.md`) — redirect сюда
