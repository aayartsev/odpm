# Golden core venv

С **4.7+** в fresh-сценариях (`developer`, `server`) odpm может переиспользовать **ядро** виртуального окружения (bootstrap + `odoo/requirements.txt` + implicit-пакеты) по ключу `venv_lock_hash`. Extras проекта (`requirements_txt`, debugpy, stubs) по-прежнему ставятся через `sync_extras_requirements` и не входят в golden.

Дополняет [общий кэш wheel](wheel-cache.md) (скачивание). CI `baked` **не** использует golden: образ уже содержит свой `.venv`.

## Переменные

| Переменная | Назначение | По умолчанию |
|------------|------------|--------------|
| `ODPM_GOLDEN_VENV` | `0` / `false` — отключить golden | включено (`1`) |
| `ODPM_GOLDEN_VENV_ROOT` | Каталог шаблонов на хосте (для mounts) | `~/.odpm/venvs` |

`ODPM_GOLDEN_VENV` из layered `.env` / process env попадает в `environment` сервиса `odoo` при генерации compose, поэтому `ODPM_GOLDEN_VENV=0` в `~/.odpm/.env` отключает golden внутри контейнера. `ODPM_GOLDEN_VENV_ROOT` влияет на host mount (через merge dotenv + process env).

Пока шаблон пишется, в каталоге golden есть маркер `.incomplete` — `golden_exists` и clone его игнорируют, `.lock` пишется только после freeze/meta.

## Layout

```text
${ODPM_GOLDEN_VENV_ROOT:-~/.odpm/venvs}/
└── <venv_lock_hash>/
    ├── .venv/                          # core-only
    ├── .lock
    ├── meta.json
    └── core-requirements.freeze.txt
```

В контейнере каталог монтируется в `/cache/odpm/venvs` (developer/server).

## Поведение при recreate

1. Если golden для текущего `venv_lock_hash` есть — клон в project `.venv` (`clonevirtualenv`, иначе install из freeze + hardlink/wheel cache).
2. Иначе — `install_core_fresh`, затем заполнение golden store.
3. Всегда — `sync_extras_requirements`.

## Fleet

На worker в `~/.odpm/.env`:

```ini
ODPM_GOLDEN_VENV_ROOT=/var/lib/odpm/venvs
ODPM_WHEEL_CACHE_ROOT=/var/cache/odpm
```

Права: runtime user контейнера (`9999:9999` / `odoo`) или общая группа.

## Отключение

```ini
ODPM_GOLDEN_VENV=0
```

Восстанавливает установку ядра через `install_core_fresh` без store.
