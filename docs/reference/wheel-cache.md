# Общий кэш wheel (pip / uv)

С **4.7+** odpm может делить **download-кэш** pip и uv между проектами на одном хосте. Это не общий `.venv`: у каждого проекта по-прежнему свой `site-packages`. Кэш ускоряет повторную установку тех же пакетов (тот же Python / те же wheel).

См. также [golden core venv](golden-venv.md) (переиспользование уже собранного ядра `.venv`).

## Переменные

| Переменная | Назначение | По умолчанию |
|------------|------------|--------------|
| `ODPM_WHEEL_CACHE_ROOT` | Корень общего кэша на хосте | `~/.odpm/cache` |
| `PIP_CACHE_DIR` | Если задан явно — odpm **не** переопределяет | `{root}/wheels/<python_version>` |
| `UV_CACHE_DIR` | Если задан явно — odpm **не** переопределяет | `{root}/uv` |

Значения берутся так: layered `.env` (`~/.odpm/.env` → project `.env`) как база, **process env перекрывает** dotenv. Host mounts читают этот merge при генерации compose; внутри контейнера пути кэша — `/cache/odpm/...` (mount). `ODPM_GOLDEN_VENV` из dotenv пробрасывается в environment сервиса `odoo`. См. [env-dotenv.md](env-dotenv.md).

## Layout на хосте

```text
${ODPM_WHEEL_CACHE_ROOT:-~/.odpm/cache}/
├── uv/
└── wheels/
    ├── 3.10/
    ├── 3.11/
    ├── 3.12/
    └── 3.13/
```

В контейнере (developer / server) те же каталоги монтируются в:

- `PIP_CACHE_DIR=/cache/odpm/wheels/<python_version>`
- `UV_CACHE_DIR=/cache/odpm/uv`

Per-project mount `data/odoo/home/.../.cache` остаётся для прочих данных; wheel cache — отдельный global mount.

## Когда работает

| Сценарий | Поведение |
|----------|-----------|
| `developer` / `server` | Env + compose mounts на `/cache/odpm/...` |
| `ci` (baked) | Host-side bake читает `ODPM_WHEEL_CACHE_ROOT` из layered dotenv + process env; mount не добавляется (venv уже в образе). Download cache внутри `docker build` требует BuildKit cache mount — отдельно. |

## Fleet / shared workers

На worker удобно задать в `~/.odpm/.env`:

```ini
ODPM_WHEEL_CACHE_ROOT=/var/cache/odpm
```

Каталог должен быть доступен runtime-пользователю контейнера (часто `9999:9999` / `odoo`) или группе docker с `chmod 2775`.

## Отключение / override

- Задайте свой `PIP_CACHE_DIR` / `UV_CACHE_DIR` — odpm их не тронет.
- Не задавайте `ODPM_WHEEL_CACHE_ROOT`, если достаточно `~/.odpm/cache`.
