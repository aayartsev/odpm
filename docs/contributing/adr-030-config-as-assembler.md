# ADR-030: Config как сборщик снимка проекта

## Status

Accepted (4.8-dev track).

## Context

`Config` остаётся центром bootstrap: загружает настройки и манифест, держит срезы, подключает git и odoo.conf. Снаружи слишком много кода всё ещё воспринимает его как «весь контекст в одном объекте», хотя для чтения уже есть [`HostProjectContext`](../../dev_project/host/context.py) и порты ([ADR-003](adr-003-host-ports-vs-config.md)), а данные внутри уже разложены по модулям `config/`.

Нужен явный контракт: **собрать** vs **потреблять**, без массового удаления `Config` и без запрета `bootstrap.config` там, где шов ещё не готов.

## Decision

1. **`Config` — сборщик** при `OdpmPipeline.setup` (фазы bootstrap) + хранилище срезов. Не «общая корзина» для новых вызовов.

2. **Потребление:**
   - оценка плана / шагов подготовки → `host_ctx` и порты;
   - выполнение → `BootstrapHandle` и координаторы (`git_repos`, …);
   - сырой `bootstrap.config` — только пока нет узкого accessor на handle; в `prepare/steps_*.py` и `prepare/runtime.py` запрещён (срезы A–B).

3. **Не раздувать плоский фасад:** новые команды и шаги не добавляют `bind_slice` / плоские свойства на `Config` ради удобства вызова. Предпочтительны порты, контекст или метод handle.

4. **Первая версия (этот ADR):** карта зон ([config-zones.md](config-zones.md)); на `BootstrapHandle` — `env_resolver`, `odoo_conf`, `pd_manager`; `PrepareContext` переводит `env_resolver` / `rebuild_compose_template` на handle; `odoo_conf` на handle доступен для прямых вызовов и следующих шагов (пока не все места вызова переведены); `ctx.config` остаётся для хвостов; правило для агентов в `.cursor/rules/`.

5. **Срез A (выполнен):** шаги secrets, sources и compose generate в `prepare/steps_*.py` не читают сырой `bootstrap.config` / `ctx.config`. На `BootstrapHandle` — `secrets_session`; сценарий шага — хелперы `PrepareContext`. Запрет в шагах держит `tests/test_prepare_config_coupling.py`. Команды `odpm` для пользователя не меняются. Хелперы по-прежнему могут вызывать API, которые принимают `Config`.

6. **Срез B (выполнен):** оценка IDE в `prepare/runtime.py` через методы `RuntimePorts`; сброс кэша превью — `BootstrapHandle.clear_runtime_config_preview_cache`; превью compose — `ComposePreviewPort.run_with_mutable_snapshot` без `runtime_cache_config` у вызывающего кода. Coupling: `steps_*.py` + `runtime.py`. Поведение команд не меняется.

7. **Вне срезов A–B:** снятие `PrepareContext.config`; отвязка `CreateProjectEnvironment` / compose service builder; публичные shims `bind_slice`; вынос runtime-фасада с `Config`.

## Consequences

- Контрибьюторы и агенты видят, куда смотреть вместо «дай весь Config».
- Поведение `odpm` для пользователя не меняется.
- ADR-003 остаётся про порты; эта запись фиксирует роль сборщика и запрет раздувать фасад.

## References

- [ADR-003](adr-003-host-ports-vs-config.md)
- [config-zones.md](config-zones.md)
- Plan: `.cursor/plans/config_zones_contract_f41d371a.plan.md`
- Slice A: `.cursor/plans/config_handle_prepare_56471ad4.plan.md`
- Slice B: `.cursor/plans/config_roadmap_b_9498b8e7.plan.md`
