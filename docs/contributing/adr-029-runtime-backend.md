# ADR-029: Движок запуска стека (Compose)

## Status

Accepted (4.8-dev track).

## Context

После prepare odpm поднимает стек через Docker Compose. Логика `ensure_base_image` + `docker compose up` была спрятана внутри `RuntimeCoordinator.start_containers`, поэтому в `odpm plan` не было явного шага «базовый образ», а смена движка запуска (Helm / Kustomize) потребовала бы переписывать координатор.

Сборка CI-образа уже имеет сменный бэкенд (`docker` / `kaniko`, ADR-027). Для **запуска** стека нужен аналогичный контракт, без смены поведения `odpm up` в первой версии.

Имя пакета `dev_project/runtime_backend/` не путать с `prepare/runtime.py` (шаги IDE / слоёв / оценки плана).

## Decision

1. **Протокол движка** (`RuntimeBackend`): `ensure_base_image`, `up`; заготовки `down` / `logs` / `exec` объявлены; у Compose — явная ошибка «не реализовано». Команды `odpm down` / `logs` в CLI в этой версии **не** добавляем.

2. **Список аргументов Compose** (`build_compose_up_argv`) — только у адаптера Compose, не в общем протоколе. Координатор проксирует для тестов и `odpm_pipeline`.

3. **Единственная реализация:** `ComposeRuntimeBackend`. Переменной окружения / флага выбора движка нет.

4. **Видимые шаги:** `runtime.ensure_base` и `compose.up` появляются вместе (или вместе отсутствуют). Id `compose.up` сохраняем. Отдельный probe «образ уже есть» в плане не делаем.

5. **Проводка:** после гейтов (снимок БД, секреты, `pre_up`) — реестр `LAUNCH_STEPS` через `execute_launch_steps` (повторная проверка тех же условий, что у видимости `compose.up` в плане). `start_containers()` — тот же реестр с `force=True`. Обёртка KeyboardInterrupt вокруг блока подъёма сохраняется.

6. **Вне этой версии:** второй движок и переключатель; команды down/logs на CLI; нейтральный формат стека вместо `HostProjectContext`; переименование `compose.up` → `runtime.up`; IDE в том же движке.

## Consequences

- `odpm plan` показывает группу запуска с двумя шагами; поведение `odpm up` для пользователя то же.
- Задел под Helm/Kustomize без смены сигнатуры протокола для `down`/`logs`/`exec`.
- Документация: `runtime-backend.md`, `cli.md` (шаги плана).

## References

- Plan: `.cursor/plans/runtime_backend_compose_c46f7b1c.plan.md`
- Related: ADR-027 (image build backends), `prepare-zones.md`
