# Локальные секреты для Odoo-модулей

Сценарии **`developer`** и **`server`** могут передать произвольные ключи в контейнер Odoo через **фиксированный путь** `/run/odpm/secrets.json` (переменная окружения **`ODPM_SECRETS_PATH`**). В сценарии **`ci`** mount с хоста **отключён** — секреты в образ не попадают этим механизмом (см. [CI в Actions](#ci-github-actions-developerserver-pipeline)).

## Зачем это нужно

Модули интеграции часто требуют API-ключи, токены, пароли внешних сервисов. Их **не следует** класть в `odpm.json` или `user_settings.json` (часто в git) и **неудобно** дублировать в compose `environment:` (видно в `docker compose config`).

odpm даёт отдельный контракт: вы храните значения в `.odpm/secrets.json` на хосте; в контейнере модуль всегда читает один путь.

## Файлы в проекте

| Файл | В git | Кто пишет | Назначение |
|------|-------|-----------|------------|
| `.odpm/secrets.example.json` | да | odpm при init | шаблон ключей без реальных значений |
| `.odpm/secrets.json` | нет | вы или `--secrets-file` | **source** — единственное место правки на хосте |
| `.odpm/runtime/secrets.json` | нет | odpm (`secrets.materialize`) | **runtime** — монтируется в контейнер |

При `odpm --init` копируется только **`secrets.example.json`**. Файл **`secrets.json`** создаётся вручную, копированием из example, или импортом через CLI.

Структура каталога: [project-layout](../reference/project-layout.md). Сгенерированные артефакты: [generated-files](../reference/generated-files.md).

## Формат (schema v1)

```json
{
    "schema_version": 1,
    "secrets": {
        "payment_provider.api_key": "sk_test_...",
        "custom_integration.token": "..."
    }
}
```

- `schema_version` обязателен, только `1`
- `secrets` — объект «строка → строка»; ключи плоские (часто с точкой: `service.field`)
- Неверный JSON или типы — ошибка при import/materialize

## Обязательные секреты в `odpm.json` (4.7)

Если модули проекта **не работают** без API-ключей, объявите это в manifest v2:

```json
"secrets": {
  "required": true,
  "keys": ["payment_provider.api_key"]
}
```

Ключи можно не дублировать — достаточно `"required": true`: odpm проверит **наличие** `.odpm/secrets.json`. Список ключей в сообщении об ошибке берётся из `secrets.example.json` только как подсказка. Для строгой проверки конкретных ключей укажите `keys` в manifest.

odpm предупредит на `odpm manifest validate` и `odpm plan`, а при полном запуске (`odpm` без `--skip-start`) остановится **до** развёртывания базы и compose, если `.odpm/secrets.json` отсутствует или содержит заглушки. См. [поля `secrets`](../../reference/odpm-json.md#блок-secrets-обязательные-локальные-секреты-47).

## `${@secret:}` в manifest (sidecar / hooks)

Для **вспомогательных** сервисов (эмуляторы, прокси) значения из `.odpm/secrets.json` можно подставить в manifest:

```json
"services": {
  "armtek": {
    "image": "armtek:latest",
    "environment": {
      "APILOGIN": "${@secret:partner_armtek.armtek.apilogin}",
      "APIPASS": "${@secret:partner_armtek.armtek.apipass}"
    }
  }
}
```

- Значения **осознанно** попадают в generated `docker-compose.yml` (файл не в git).
- Нужен уже существующий `.odpm/secrets.json` **или** `--secrets-file` в этом запуске; иначе `ConfigError`.
- Gate `${@secret:}` при bootstrap проверяет только **effective manifest** активного `ODPM_SCENARIO` (тот же slice, что compose / `load_manifest`). Ссылки только в других `scenarios.*` не учитываются. Пример: `@secret` только в `scenarios.developer` **не** требует `.odpm/secrets.json` при `ODPM_SCENARIO=ci`.
- Для **Odoo-модулей** по-прежнему читайте `/run/odpm/secrets.json` в контейнере — не дублируйте секреты в `environment` сервиса `odoo`, если достаточно файлового mount.

## Быстрый старт

### Вариант A: из шаблона

```bash
cp .odpm/secrets.example.json .odpm/secrets.json
# отредактируйте значения в .odpm/secrets.json
odpm --skip-start
docker compose up -d
```

### Вариант B: import при инициализации

```bash
odpm --init file:///path/to/developing-project \
     --secrets-file /secure/vault/client-secrets.json
odpm --skip-start
```

### Вариант C: import на существующем проекте

```bash
odpm --secrets-file ~/Downloads/new-secrets.json --skip-start
docker compose up -d
```

Содержимое копируется в `.odpm/secrets.json` с правами **`0600`**. Исходный файл **не удаляется**.

## Полный цикл после изменения секретов

1. Отредактируйте **`.odpm/secrets.json`** (или снова вызовите `--secrets-file`).
2. Запустите **`odpm --skip-start`** — шаг **`secrets.materialize`** обновит `.odpm/runtime/secrets.json` и пересоберёт `docker-compose.yml` при необходимости.
3. Перезапустите контейнер Odoo: **`docker compose up -d`** (или полный `odpm`).
4. Проверьте mount (см. ниже).

Если **`secrets.json` удалён**, при следующем materialize stale **`.odpm/runtime/secrets.json`** удаляется, volume и `ODPM_SECRETS_PATH` из compose пропадают.

## Проверка, что mount работает

В `docker-compose.yml` сервиса `odoo` (при наличии source):

- переменная `ODPM_SECRETS_PATH=/run/odpm/secrets.json`
- volume `.odpm/runtime/secrets.json:/run/odpm/secrets.json:ro,Z`

Внутри контейнера:

```bash
docker compose exec odoo test -f /run/odpm/secrets.json && echo OK
docker compose exec odoo python3 -c "import json; print(list(json.load(open('/run/odpm/secrets.json'))['secrets']))"
```

Вторую команду используйте только для отладки; **не логируйте значения** в production.

## Контракт для кода Odoo-модуля

```python
import json
from pathlib import Path

SECRETS_PATH = Path("/run/odpm/secrets.json")

def load_odpm_secrets() -> dict[str, str]:
    if not SECRETS_PATH.is_file():
        return {}
    data = json.loads(SECRETS_PATH.read_text(encoding="utf-8"))
    return dict(data.get("secrets") or {})
```

Модулю не важны пути на хосте — только `/run/odpm/secrets.json`. При отсутствии файла возвращайте пустой dict или обрабатывайте ошибку по логике модуля.

Типичное использование: запись в `ir.config_parameter` при установке модуля или чтение при каждом запросе (без кеширования секретов в логах).

## Plan и materialize

- Prepare-шаг **`secrets.materialize`** (перед `compose.service`) копирует source → runtime.
- **`odpm plan`** показывает шаг как `update` / `noop` / `skip` (в CI — `skip`).
- **`odpm plan --plan-show-diff`** для secrets — только **summary** (например «will materialize 3 secret keys»), **без значений**.

Пример:

```bash
odpm plan --skip-start
odpm plan --skip-start --plan-show-diff
```

## Безопасность

- **`.odpm/secrets.json`** добавляется в **`.odpm/.gitignore`** автоматически при import/materialize.
- Если файл есть, но не в gitignore — **`odpm plan`** выдаёт предупреждение.
- Не коммитьте реальные значения; в git держите **`secrets.example.json`** с `REPLACE_ME`.
- Не кладите секреты приложения в **`odpm.json`**, **`user_settings.json`**, корневой **`.env`** (для структурированных ключей).
- Подробнее: [безопасность](security.md).

## По сценариям

| Сценарий | Mount secrets | Примечание |
|----------|---------------|------------|
| `developer` | да | типичный локальный dev |
| `server` | да | доставьте `secrets.json` на VM (`--secrets-file` или копирование) |
| `ci` | нет | runtime config в образе; секреты приложения — отдельный процесс деплоя |

### CI (GitHub Actions, developer/server pipeline)

В сценарии **`ci`** (`odpm --build-image`) mount secrets с хоста **по-прежнему отключён** — секреты в образ этим механизмом не попадают.

Для **локального developer/server pipeline** в Actions используйте ephemeral JSON и `--secrets-file`:

```yaml
- name: Materialize module secrets for odpm project
  run: |
    cat > /tmp/odpm-ci-secrets.json <<'EOF'
    {"schema_version":1,"secrets":{"payment.api_key":"${{ secrets.MODULE_PAYMENT_API_KEY }}"}}
    EOF
    chmod 600 /tmp/odpm-ci-secrets.json
    odpm --secrets-file /tmp/odpm-ci-secrets.json --skip-start
  working-directory: /path/to/odpm-project
```

Репозиторий odpm проверяет контракт в **`tests/test_ci_secrets_smoke.py`** (job `compose-smoke` в `ci-docker.yml`). Значения секретов в логи не выводить.

**Follow-up (Phase B):** bake secrets в CI-образ при `ODPM_SCENARIO=ci` — отдельная задача.

## Отличие от `.env` и паролей Odoo

| Механизм | Назначение |
|----------|------------|
| `.env` | порты, каталоги, `ODPM_SCENARIO` |
| `user_settings.json` | пароли БД/админа Odoo, модули, git |
| `.odpm/runtime/config.json` | служебный контракт odpm host→container |
| **`.odpm/secrets.json`** | произвольные ключи **ваших модулей** (payment, SMTP API, …) |

## Работа в команде

1. Заполните **`.odpm/secrets.example.json`** с перечнем нужных ключей.
2. Каждый разработчик создаёт локальный **`.odpm/secrets.json`** (не в git).
3. При добавлении ключей в проект можно сделать так: `cp .odpm/secrets.example.json .odpm/secrets.json` и заполнить значения, либо `odpm --secrets-file …` из корпоративного хранилища.

## Устранение неполадок

| Симптом | Что проверить |
|---------|----------------|
| `/run/odpm/secrets.json` нет в контейнере | Есть ли `.odpm/secrets.json`? Запускали `odpm --skip-start`? Сценарий не `ci`? |
| Старые значения после правки | `odpm --skip-start` + `docker compose up -d` |
| Ошибка schema | `schema_version: 1`, все значения — строки |
| Compose без volume | Удалите source и перегенерируйте compose; или добавьте source и снова `odpm --skip-start` |

Параметр CLI: [`--secrets-file`](../reference/cli.md).
