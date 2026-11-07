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
   - сырой `bootstrap.config` — только пока нет узкого accessor на handle.

3. **Не раздувать плоский фасад:** новые команды и шаги не добавляют `bind_slice` / плоские свойства на `Config` ради удобства вызова. Предпочтительны порты, контекст или метод handle.

4. **Первая версия (этот ADR):** карта зон ([config-zones.md](config-zones.md)); на `BootstrapHandle` — `env_resolver`, `odoo_conf`, `pd_manager`; `PrepareContext` переводит `env_resolver` / `rebuild_compose_template` на handle; `odoo_conf` на handle доступен для прямых вызовов и следующих шагов (пока не все места вызова переведены); `ctx.config` остаётся для хвостов; правило для агентов в `.cursor/rules/`.

5. **Вне этой версии:** убрать `PrepareContext.config` и остальные `bootstrap.config` в execute; отвязать `CreateProjectEnvironment` / compose service builder; снять публичные shims `bind_slice`; вынести runtime-фасад с `Config`.

## Consequences

- Контрибьюторы и агенты видят, куда смотреть вместо «дай весь Config».
- Поведение `odpm` для пользователя не меняется.
- ADR-003 остаётся про порты; эта запись фиксирует роль сборщика и запрет раздувать фасад.

## References

- [ADR-003](adr-003-host-ports-vs-config.md)
- [config-zones.md](config-zones.md)
- Plan: `.cursor/plans/config_zones_contract_f41d371a.plan.md`
