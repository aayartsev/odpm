# Миграция odpm.json v1 → v2

Менеджер **odpm 4.4** читает оба формата без обязательной миграции. Nested **manifest v2** — opt-in: расширения (`services`, `hooks`, `locks` в манифесте), явный `requires_odpm`.

## Когда мигрировать

| Ситуация | Рекомендация |
|----------|--------------|
| Flat v1, команда не меняет manifest | **Не мигрировать** — всё работает как раньше |
| Нужны declarative compose services (Mailpit и др.) | v2 + блок `services` |
| Patch env/ports у `odoo` / `db` | v2 + `service_patches` (см. [ADR-009](https://github.com/aayartsev/odpm/blob/4.6.0-dev/docs/contributing/adr-009-compose-service-patch.md)) |
| Locks в git вместо только `.odpm/deps.lock.json` | v2 + `locks` |
| Lifecycle hooks в manifest | v2 + `hooks` |
| Новый проект на 4.4 | Можно сразу v2 или flat v1 (odpm пишет v1 по умолчанию) |

## Команда migrate

```bash
cd /path/to/developing/project
odpm manifest migrate          # unified diff на stdout
odpm manifest migrate --write  # записать odpm.json
```

Перед `--write` сохраните копию или закоммитьте текущий `odpm.json`.

## Что переносится

| Источник (v1 / артефакты) | Поле v2 |
|---------------------------|---------|
| `python_version` | `python` |
| `odoo_git_link`, `odoo_build_date` | `platform.git`, `platform.build_date` |
| `distro_name`, `distro_version` | `distro.name`, `distro.version` |
| `postgres_version` | `postgres` |
| `dependencies` | `dependencies` |
| `requirements_txt` | `requirements` |
| `developing_project` в `user_settings.json` | `developing.git` |
| `database` или `db_creation_data` | `database` |
| `.odpm/deps.lock.json` | `locks.git` (+ venv hash при наличии) |

## Пример до и после

**v1 flat (фрагмент):**

```json
{
  "odpm_version": "4.0",
  "python_version": "3.12",
  "distro_name": "debian",
  "distro_version": "12",
  "postgres_version": "16",
  "odoo_version": "19.0",
  "odoo_git_link": "https://github.com/odoo/odoo.git 19.0",
  "dependencies": [],
  "requirements_txt": []
}
```

**v2 nested (эквивалент + расширения):**

```json
{
  "manifest_schema": 2,
  "requires_odpm": "4.6.0",
  "platform": {
    "git": "https://github.com/odoo/odoo.git 19.0",
    "build_date": "latest"
  },
  "python": "3.12",
  "distro": { "name": "debian", "version": "12" },
  "postgres": "16",
  "dependencies": [],
  "requirements": [],
  "developing": { "git": "file:///path/to/developing" },
  "services": {
    "mailpit": {
      "image": "axllent/mailpit",
      "restart": "unless-stopped",
      "ports": ["8025:8025", "1025:1025"]
    }
  },
  "hooks": {
    "post_prepare": [["echo", "prepare done"]],
    "pre_up": []
  },
  "locks": {
    "git": {}
  }
}
```

## После миграции

1. **`odpm plan`** — проверьте шаги prepare (в т.ч. `compose.fragments`, `compose.patch.*`) и предупреждения об источнике lock.
2. **`odpm up --skip-start`** — materialize без поднятия контейнеров.
3. **Locks** — см. [Locks после миграции (v2)](#locks-после-миграции-v2).
4. **Откат** — восстановите v1 из git; dual-read не требует v2.

## Locks после миграции (v2)

| Действие | Поведение |
|----------|-----------|
| Обычный prepare | Чтение пинов из **`locks.git`** в `odpm.json` (канон) |
| `odpm --update-lock` | Пересчёт коммитов с диска → запись **только** в `.odpm/deps.lock.json` |
| `odpm --update-lock --sync-manifest-locks` | То же + запись `locks.git` в `odpm.json` (opt-in, **developer**, v2) |
| Ручное изменение SHA | Редактируйте **`locks.git`**; затем `--update-lock`, чтобы синхронизировать deps.lock |
| Расхождение manifest ↔ deps.lock | Warning в `odpm plan` и в логе на `git.lock_verify`; prepare использует manifest |

**Dual-write policy:** по умолчанию odpm **не** перезаписывает `locks.git` при `--update-lock`. Канон остаётся в manifest; deps.lock — операционный артефакт. Opt-in: **`--sync-manifest-locks`** вместе с `--update-lock` (сценарий `developer`, `manifest_schema: 2`) записывает `locks.git` из собранного deps.lock. После смены зависимостей: `--update-lock`, закоммитьте обновлённый `.odpm/deps.lock.json` и при необходимости перенесите SHA в `locks.git` (или используйте `--sync-manifest-locks`, либо `odpm manifest migrate --write` из актуального deps.lock).

Подробнее: [deps-lock.md](deps-lock.md#два-источника-lock-v1-flat-vs-v2-nested).

## Совместимость

- **`odpm_version: "4.0"`** в flat v1 — контрактная строка формата, **не** версия менеджера.
- **`requires_odpm: "4.6.0"`** в v2 — минимальная версия установленного odpm (semver); новые проекты получают текущий `RELEASE_VERSION`.
- Подробнее: [odpm.json](odpm-json.md), [plugins.md](plugins.md), [ADR-001](https://github.com/aayartsev/odpm/blob/4.6.0-dev/docs/contributing/adr-001-extensions-and-manifest-v2.md).
