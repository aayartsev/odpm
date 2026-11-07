# ADR-030: Config как сборщик снимка проекта

## Status

Accepted (4.8-dev track).

## Context

Внутренний сборщик снимка — [`AssembledProject`](../../dev_project/config/config.py) (файл `config/config.py`; публичного типа `Config` нет). Он загружает настройки и манифест, держит срезы, подключает git и odoo.conf. Снаружи — [`HostProjectContext`](../../dev_project/host/context.py) и порты ([ADR-003](adr-003-host-ports-vs-config.md)); данные внутри разложены по модулям `config/`.

Нужен явный контракт: **собрать** vs **потреблять**. С кампании G у ручки нет публичного `.config`; сборка `host_ctx` / портов — фабриками в `config/`. С кампании H класс переименован в `AssembledProject`, фасады git/symlink/nested/odoo.conf-docker сняты со сборщика (только через ручку); гейт `tests/test_no_public_config.py`.

## Decision

1. **`AssembledProject` — сборщик** при `OdpmPipeline.setup` (фазы bootstrap) + хранилище срезов. Не «общая корзина» для новых вызовов. Публичного символа `Config` нет.

2. **Потребление:**
   - оценка плана / шагов подготовки → `host_ctx` и порты;
   - выполнение → `BootstrapHandle` и координаторы (`git_repos`, …);
   - сырой снимок снаружи ручки недоступен (`_assembled` только внутри handle / `config/`); в `prepare/steps_*.py` и `prepare/runtime.py` запрещены строки `bootstrap.config` / `ctx.config`.

3. **Не раздувать плоский фасад:** новые команды и шаги не добавляют `bind_slice` / плоские свойства на сборщик ради удобства вызова. Предпочтительны порты, контекст или метод handle.

4. **Первая версия (этот ADR):** карта зон ([config-zones.md](config-zones.md)); на `BootstrapHandle` — `env_resolver`, `odoo_conf`, `pd_manager`; `PrepareContext` переводит `env_resolver` / `rebuild_compose_template` на handle; `odoo_conf` на handle доступен для прямых вызовов и следующих шагов (пока не все места вызова переведены); правило для агентов в `.cursor/rules/`.

   - сырой снимок снаружи ручки недоступен (`_assembled` только внутри handle / `config/`); в `prepare/steps_*.py` и `prepare/runtime.py` запрещены строки `bootstrap.config` / `ctx.config`.

6. **Срез B (выполнен):** оценка IDE в `prepare/runtime.py` через методы `RuntimePorts`; сброс кэша превью — `BootstrapHandle.clear_runtime_config_preview_cache`; превью compose — `ComposePreviewPort.run_with_mutable_snapshot` без `runtime_cache_config` у вызывающего кода. Coupling: `steps_*.py` + `runtime.py`. Поведение команд не меняется.

7. **Срез C (выполнен):** алиас `PrepareContext.config` снят; сырой снимок только через `ports.bootstrap` / хелперы. Поведение команд не меняется.

8. **Срез D (выполнен):** публичные входы сборщика compose, менеджера ссылок, исходников сервисов и drift — на `BootstrapHandle`.

9. **Срез E (выполнен):** `CreateProjectEnvironment` получает
   `BootstrapHandle` и не публикует `.config`; состояние запуска доступно через
   `BootstrapHandle.runtime` / `AssembledProject.runtime`. Плоский runtime-фасад и
   автоматически привязанные свойства срезов (`bind_slice_properties`) удалены:
   внутри сборщика используются явные `user_settings`, `project_settings`,
   `docker_layout`, `addon_layout`.

10. **Кампания G (выполнена):** у `BootstrapHandle` нет публичного `.config`
    (снимок — `_assembled`); фабрики `ports_from_assembled` /
    `host_context_from_assembled` в [`config/assembly.py`](../../dev_project/config/assembly.py);
    публичные `HostProjectContext.from_config` и `ports_from_config` сняты с
    `host/`; `config.state` не импортирует `host` во время выполнения (нет цикла
    `config.state` ↔ `host`).

11. **Кампания H (выполнена):** класс сборщика — `AssembledProject` (не публичный
    `Config`); реэкспорт `Config` из `dev_project.config` снят; методы-фасады
    `handle_git_link` / symlink helpers / `apply_nested_compatibility` /
    `generate_odoo_conf_docker_data` только на ручке; контрактный гейт
    [`tests/test_no_public_config.py`](../../tests/test_no_public_config.py).

## Consequences

- Контрибьюторы и агенты видят, куда смотреть вместо «дай весь Config».
- Поведение `odpm` для пользователя не меняется.
- ADR-003 остаётся про порты; эта запись фиксирует роль сборщика (`AssembledProject`) и запрет раздувать фасад.

## References

- [ADR-003](adr-003-host-ports-vs-config.md)
- [config-zones.md](config-zones.md)
- Plan: `.cursor/plans/config_zones_contract_f41d371a.plan.md`
- Slice A: `.cursor/plans/config_handle_prepare_56471ad4.plan.md`
- Slice B: `.cursor/plans/config_roadmap_b_9498b8e7.plan.md`
- Slices C–E: `.cursor/plans/config_roadmap_cde_41d7995e.plan.md`
