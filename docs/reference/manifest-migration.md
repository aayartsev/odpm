# Миграция odpm.json v1 → v2

Менеджер **odpm 4.4** читает оба формата без обязательной миграции. Nested **manifest v2** — opt-in: расширения (`services`, `hooks`, `locks` в манифесте), явный `requires_odpm`.

## Когда мигрировать

| Ситуация | Рекомендация |
|----------|--------------|
| Flat v1, команда не меняет manifest | **Не мигрировать** — всё работает как раньше |
| Нужны declarative compose services (Mailpit и др.) | v2 + блок `services` |
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
  "requires_odpm": "4.4",
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

1. **`odpm plan`** — проверьте шаги prepare (в т.ч. `compose.fragments`).
2. **`odpm up --skip-start`** — materialize без поднятия контейнеров.
3. **Locks** — `DepsLockManager` читает `locks.git` при `manifest_schema: 2`; `.odpm/deps.lock.json` синхронизируется при `--update-lock`.
4. **Откат** — восстановите v1 из git; dual-read не требует v2.

## Совместимость

- **`odpm_version: "4.0"`** в flat v1 — контрактная строка формата, **не** версия менеджера.
- **`requires_odpm: "4.4"`** в v2 — минимальная версия установленного odpm (semver).
- Подробнее: [odpm.json](odpm-json.md), [plugins.md](plugins.md), [ADR-001](../contributing/adr-001-extensions-and-manifest-v2.md).
