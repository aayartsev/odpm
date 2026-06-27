# Demo-проекты для ручного тестирования

Публичный репозиторий **[odoo_demo_project](https://github.com/aayartsev/odoo_demo_project)** — минимальный набор модулей Odoo с `odpm.json`. В **остальной документации odpm** в примерах используется только **Odoo 19.0** (`--branch 19.0`, каталог `odoo_demo_project-19`). Обёртки для **17.0** и **18.0** и матрица сценариев — **только в этой статье**.

Для **полного** E2E (клон платформы Odoo, образы, HTTP `/web`) одного git-репозитория недостаточно: нужен **каталог окружения odpm** на диске — тот же паттерн, что в [локальной разработке с нуля](../getting-started/local-dev-from-scratch.md).

Maintainer’ы odpm держат **три обёртки** — по одной на major-версию Odoo:

| Odoo | Каталог-обёртка (пример) | Ветка модулей |
|------|--------------------------|---------------|
| 17.0 | `odoo_demo_project-17` | `17.0` |
| 18.0 | `odoo_demo_project-18` | `18.0` |
| 19.0 | `odoo_demo_project-19` | `19.0` |

Каталоги **не коммитятся** в репозиторий odpm: это локальные (или self-hosted CI) площадки. В документации пути задаются через переменные окружения, а не через `$HOME` конкретного разработчика.

## Переменные окружения

Добавьте в `~/.bashrc` или экспортируйте перед сессией:

```bash
export ODPM_DEMO_ROOT="${ODPM_DEMO_ROOT:-$HOME/projects}"
export ODPM_DEMO_17="${ODPM_DEMO_17:-$ODPM_DEMO_ROOT/odoo_demo_project-17}"
export ODPM_DEMO_18="${ODPM_DEMO_18:-$ODPM_DEMO_ROOT/odoo_demo_project-18}"
export ODPM_DEMO_19="${ODPM_DEMO_19:-$ODPM_DEMO_ROOT/odoo_demo_project-19}"
```

Для golden-path и скриптов odpm:

```bash
export ODPM_GOLDEN_PATH_PROJECT="${ODPM_GOLDEN_PATH_PROJECT:-$ODPM_DEMO_19}"
```

## Создание обёртки с нуля (19.0 — канонический пример в доке)

```bash
mkdir -p "$ODPM_DEMO_ROOT"
cd "$ODPM_DEMO_ROOT"
mkdir odoo_demo_project-19 && cd odoo_demo_project-19
odpm --init https://github.com/aayartsev/odoo_demo_project.git --branch 19.0
```

Для **17.0** / **18.0** замените суффикс каталога и `--branch` по таблице выше.

## Отличие от CI fixture

| | In-repo fixture | Demo-обёртки |
|---|-----------------|--------------|
| Путь | `tests/fixtures/minimal_odpm_project/` | `$ODPM_DEMO_*` на диске |
| Odoo platform | Нет (compose-smoke) | Полный клон и образ |
| Когда | Каждый push/PR | Ручной smoke, golden-path, регрессии |
| Время | Минуты | Первый init — до часа (клон platform) |

**Не заменяйте** `minimal_odpm_project` в обязательном CI: demo-проекты тяжёлые. См. [ci.md](ci.md).

## Быстрый smoke (~5 мин)

На уже инициализированной обёртке (Docker запущен):

```bash
cd "$ODPM_DEMO_19"
odpm plan --skip-start
odpm database status
docker compose ps
curl -sf "http://127.0.0.1:${ODOO_PORT:-8069}/web" >/dev/null && echo OK
```

Ожидание: exit code 0 у plan/status; контейнеры `Up`; HTTP OK.

## Сценарии ручного тестирования

Краткая матрица:

| ID | Сценарий | Обёртка | Связанная документация |
|----|----------|---------|-------------------------|
| S1 | Первый init и golden path | `-17` или `-18` | [local-dev-from-scratch](../getting-started/local-dev-from-scratch.md), [smoke-4.0-checklist §2C](../smoke-4.0-checklist.md) |
| S2 | `plan`, `database status`, drift | любая | [database-state](../reference/database-state.md) |
| S3 | Смена major PostgreSQL + wipe | та, где меняли PG | [database-state § major](../reference/database-state.md), [non-interactive](../operations/non-interactive.md) |
| S4 | `server` / `ci --build-image` | `-19` (новее) | [server](../scenarios/server.md), [ci](../scenarios/ci.md) |
| S5 | VS Code / debugpy attach | `-18` | [vscode-debug](../operations/vscode-debug.md) |
| S6 | `--accept-database-drift`, без TTY | любая | [non-interactive](../operations/non-interactive.md) |

Чеклист с колонками Pass/Date — в [smoke-4.0-checklist.md](../smoke-4.0-checklist.md) (разделы **2B**, **2C**, **2C golden path**). Личные заметки с таймингами — в **`docs/smoke-local.md`** (не в git, см. чеклист).

---

### S1 — Первый init и рабочий стек

**Предусловия:** Docker, git, установленный odpm, свободное место на диске.

```bash
rm -rf "$ODPM_DEMO_17"   # только для чистого прогона
mkdir -p "$(dirname "$ODPM_DEMO_17")" && cd "$(dirname "$ODPM_DEMO_17")"
mkdir "$(basename "$ODPM_DEMO_17")" && cd "$ODPM_DEMO_17"
odpm --init https://github.com/aayartsev/odoo_demo_project.git --branch 17.0
odpm -d test_db -i -u
curl -sf "http://127.0.0.1:${ODOO_PORT:-8069}/web"
```

**Pass:** окно входа Odoo в браузере; `docker compose ps` — сервисы postgres и odoo в состоянии Up.

**Автоматический аналог:** opt-in [golden-path](ci.md) (`ODPM_GOLDEN_PATH_PROJECT=$ODPM_DEMO_17 ./scripts/run_golden_path_test.sh`).

---

### S2 — Plan и состояние PostgreSQL

```bash
cd "$ODPM_DEMO_18"
odpm database status
odpm database status --format json | jq .drifts
odpm plan --skip-start
```

**Pass:** таблица status без blocking drift (или понятный список drift); plan exit 0; шаг `database.drift` — noop или run с ожидаемой причиной.

**Автоматический аналог:** `tests/test_odpm_plan_smoke.py`, `tests/test_database_drift.py`.

---

### S3 — Смена major PostgreSQL

Типичный регрессионный кейс: в `odpm.json` или настройках сменили `postgres_version`, data dir очищен.

```bash
cd "$ODPM_DEMO_18"
docker compose down
# удалить каталог данных PostgreSQL (путь из odpm database status → Data path)
odpm --accept-database-drift=postgres_major
# или интерактивно: odpm → prompt postgres_major → (b) принять
odpm
```

**Pass:** baseline обновлён (`.odpm/database/last_run.json` с новым `image_tag`); контейнер postgres поднимается; нет ошибки «блокирующий дрейф postgres_major».

Инструкция wipe в prompt **(c)** должна содержать реальный путь к data dir и флаг `--accept-database-drift=postgres_major`.

---

### S4 — Сценарии server и ci

**Server** (на `-19` или копии):

```bash
cd "$ODPM_DEMO_19"
# в .env проекта: ODPM_SCENARIO=server
odpm --skip-start
docker compose up -d
```

**Pass:** нет порта отладки в compose; postgres на `127.0.0.1`; Odoo доступен на `ODOO_PORT`.

**CI-образ:**

```bash
cd "$ODPM_DEMO_19"
# ODPM_SCENARIO=ci в .env
odpm --skip-start
odpm --build-image --image-tag odoo-demo-ci:local
```

**Pass:** образ собран; в логах нет mount исходников с хоста (см. [ci](../scenarios/ci.md)).

---

### S5 — Отладка в VS Code

```bash
cd "$ODPM_DEMO_18"
odpm --skip-start
docker compose up -d
# Attach по launch.json / instructions
```

**Pass:** debugpy слушает `DEBUGGER_PORT`; breakpoint в модуле demo-проекта срабатывает.

Подробно: [vscode-debug.md](../operations/vscode-debug.md).

---

### S6 — Non-interactive и drift

```bash
cd "$ODPM_DEMO_18"
script -q -c "odpm plan --skip-start" /dev/null   # без TTY → ошибка при drift
odpm plan --skip-start --accept-database-drift=postgres_major
```

**Pass:** без флага — понятная ошибка со списком KIND; с флагом — exit 0, baseline обновлён.

---

## Golden-path в CI

Self-hosted runner может использовать одну из обёрток:

- secret / variable `ODPM_GOLDEN_PATH_PROJECT` → путь к `$ODPM_DEMO_19` (или `$ODPM_DEMO_17` / `$ODPM_DEMO_18` для регрессий по major);
- nightly / label `run-docker` — см. [ci.md](ci.md).

Demo-обёртки **не делают** golden-path обязательным на каждый PR.

## Связанные материалы

- [Тесты репозитория odpm](tests.md)
- [Smoke checklist 4.x](../smoke-4.0-checklist.md)
