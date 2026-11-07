# Движок запуска стека

Контракт «как поднять стек после prepare» живёт в пакете [`dev_project/runtime_backend/`](../../dev_project/runtime_backend/). Это **не** то же самое, что модуль шагов плана [`prepare/runtime.py`](../../dev_project/prepare/runtime.py) (IDE, слои образа, оценка `compose.up` в `odpm plan`).

## Зачем

После подготовки окружения odpm поднимает Docker Compose. Логика раньше сидела целиком в [`RuntimeCoordinator.start_containers`](../../dev_project/runtime_coordinator.py). Вынос в движок:

- в `odpm plan` видны отдельные шаги запуска;
- позже можно добавить второй движок (Helm / Kustomize) без переписывания координатора.

В 4.8 реализация **только Compose**; переключателя нет.

## Карта

| Часть | Роль |
|-------|------|
| `protocol.RuntimeBackend` | Общий контракт: `ensure_base_image`, `up`, заготовки `down` / `logs` / `exec` |
| `compose.ComposeRuntimeBackend` | Адаптер Compose; **только здесь** список аргументов `docker compose up` (`build_compose_up_argv`) |
| `factory.get_runtime_backend` | Всегда возвращает Compose |
| `registry.LAUNCH_STEPS` | Порядок выполнения после гейтов: `runtime.ensure_base` → `compose.up` |

Координатор держит фасад `start_containers()` (для тестов и `odpm_pipeline`: тот же реестр с `force=True`) и проксирует `build_compose_up_argv` к адаптеру. После снимка БД, секретов и хуков `pre_up` вызывается `execute_launch_steps` (без `force` — те же условия видимости, что у `compose.up` в плане). Адаптер каждый раз создаётся заново с актуальным `host_ctx`.

## Шаги в плане

Если стек будет подниматься (те же условия, что у `compose.up`), в плане оба шага — `run`:

1. `runtime.ensure_base` — обеспечить базовый образ Odoo;
2. `compose.up` — `docker compose up` (id без переименования).

При `--skip-start` / `--update-lock` и т.п. **нет** ни того, ни другого. Отдельной проверки «образ уже на месте» в плане нет: при выполнении `ensure_base_image` остаётся идемпотентным.

Группа таблицы плана: «запуск» (`runtime`). Хуки `hooks.pre_up` в плане стоят **перед** `runtime.ensure_base` / `compose.up`, как в реальном порядке после prepare.

## Связанные документы

- [ADR-029](adr-029-runtime-backend.md) — решение по контракту
- [Зоны подготовки](prepare-zones.md) — шаги до запуска
- [ADR-027](adr-027-layered-ci-images.md) — слои CI-образа (соседние шаги `image.*`, не движок запуска)
