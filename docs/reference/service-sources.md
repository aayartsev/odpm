# Service sources (git sidecar / build-контексты)

Блок **`service_sources`** в manifest v2 описывает **внешние git-репозитории** для sidecar-сервисов и `docker build` в hooks — без ручных абсолютных путей в `.env`.

См. также: [odpm.json](odpm-json.md), [ссылки на репозитории](git-links.md), [плагины](plugins.md), [deps.lock](deps-lock.md).

## Модель

| Элемент | Правило |
|---------|---------|
| `service_sources.<name>` | git-ссылка (тот же синтаксис, что `dependencies` / `platform.git`) |
| Имя `<name>` | `[a-z][a-z0-9_]*` |
| `services.<svc>.source` | необязательная ссылка на имя из effective `service_sources` |
| `${@source:<name>}` | путь после materialize (env `ODPM_SOURCE_<NAME>`) |
| `file://` | локальный override без clone |

Репозитории из `service_sources` **не** попадают в `dependencies` и **не** добавляются в `addons_path`.

## Пример manifest

```json
{
  "manifest_schema": 2,
  "requires_odpm": "4.7.0",
  "service_sources": {
    "autoparts_env": "https://github.com/org/autoparts-env.git 17.0"
  },
  "services": {
    "armtek_test": {
      "source": "autoparts_env",
      "image": "autoparts_env:emulator",
      "user": "root",
      "tty": true,
      "volumes": ["${@source:autoparts_env}/data:/data:Z"]
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
}
```

В project `.env` достаточно стандартных переменных odpm; **`DIGITAL_AUTOPARTS_ENV_DIR` не нужен**.

## Materialize

Prepare-шаг **`sources.materialize`** (после `git.materialize`, до `hooks.post_clone`):

1. Клонирует git-источники в **`${ODOO_PROJECTS_DIR}/service-sources/<name>`**
2. Для `file://` — использует указанный каталог (clone не выполняется)
3. Записывает пути в `ODPM_SOURCE_*` и **пере-expand** `services` / `service_patches` перед compose

При `--no-git-update` odpm только проверяет, что каталоги уже существуют.

## Подстановка `${@source:...}`

- Синтаксис: **`${@source:<name>}`** → env-ключ **`ODPM_SOURCE_<NAME>`** (имя в upper case)
- При чтении manifest неразрешённый `${@source:...}` в compose-полях **не падает**; путь подставляется после `sources.materialize`
- Hooks раскрывают `${@source:...}` при выполнении (когда resolver уже содержит пути)
- Поле `source` в `services.*` **не попадает** в сгенерированный compose YAML

Обратная совместимость: старый `${DIGITAL_AUTOPARTS_ENV_DIR}` из `.env` продолжает работать.

## Scenario overlays

В `scenarios.*` блок `service_sources` merge **replace-by-name** (overlay перекрывает то же имя).

## deps.lock

В `.odpm/deps.lock.json` (schema v1):

```json
"service_sources": {
  "autoparts_env": {
    "url": "https://github.com/org/autoparts-env",
    "commit": "…",
    "branch": "17.0"
  }
}
```

- `odpm --update-lock` собирает пины после materialize
- CI (strict) проверяет drift по имени источника

## Валидация

`odpm manifest validate`:

- ключи `service_sources` — по схеме и regex имени
- `services.*.source` — должно существовать в effective `service_sources`
