# Плагины и расширения odpm (4.4+)

odpm 4.4 добавляет **extension API** на host: prepare steps, compose fragments и lifecycle hooks. Плагины не получают прямой доступ к mutable `Config` — только frozen [`ExtensionHostContext`](https://github.com/aayartsev/odpm/blob/4.4-dev/dev_project/extensions/context.py).

## Три способа расширить проект

| Механизм | Где объявляется | Когда выполняется |
|----------|-----------------|-------------------|
| **Manifest `services`** | `odpm.json` v2 → `services` | Prepare `compose.fragments` + рендер `docker-compose.yml` |
| **Manifest `hooks`** | `odpm.json` v2 → `hooks` | `post_prepare` после prepare; `pre_up` перед `docker compose up` |
| **Python entry points** | `pyproject.toml` пакета | Pluggy: `odpm.prepare_steps`, `odpm.hooks`, `register_compose_fragment` |

Подробнее о полях v2: [odpm.json](odpm-json.md). ADR: [adr-001-extensions-and-manifest-v2.md](../contributing/adr-001-extensions-and-manifest-v2.md).

## Декларативный сервис (Mailpit)

Тестовый SMTP с веб-интерфейсом на порту **8025**. Добавьте в nested manifest v2:

```json
{
  "manifest_schema": 2,
  "requires_odpm": "4.4",
  "services": {
    "mailpit": {
      "image": "axllent/mailpit",
      "restart": "unless-stopped",
      "ports": ["8025:8025", "1025:1025"]
    }
  }
}
```

Тот же spec в коде: `dev_project.extensions.reference.mailpit.MAILPIT_SERVICE_SPEC`.

После `odpm up` сервис появится в сгенерированном `docker-compose.yml` (блок `{COMPOSE_SERVICE_FRAGMENTS}`). Артефакты materialize: `.odpm/compose/fragments/mailpit.yml` (gitignored).

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

Каждый элемент — либо **argv** (массив строк, выполняется в `project_dir`), либо **plugin id** (строка) для pluggy hook runner.

Порядок по ADR:

1. Все prepare steps (built-in + `odpm.prepare_steps`)
2. `hooks.post_prepare`
3. Runtime: debug profile, IDE, database drift
4. `hooks.pre_up`
5. `docker compose up`

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

## Ограничения

- Container-side `ContainerConfig` остаётся **stdlib-only** (без новых PyPI deps в образе).
- Compose YAML генерируется без PyYAML (dict → YAML renderer); сложные anchor/merge не поддерживаются.
- Конфликт имён: plugin compose fragment **перезаписывает** одноимённый service из manifest.

## См. также

- [Сгенерированные файлы](generated-files.md) — `.odpm/compose/fragments/`
- [Примеры сервисов](https://github.com/aayartsev/odpm/blob/4.4-dev/dev_project/plugins/services_ru.md) (legacy markdown)
- Устаревший черновик плагинов: [plugins/todo_ru.md](https://github.com/aayartsev/odpm/blob/4.4-dev/dev_project/plugins/todo_ru.md) → redirect сюда
