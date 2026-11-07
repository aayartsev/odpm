# Зоны шагов подготовки

Карта видимых шагов `odpm prepare` / `odpm plan` (реестр в [`dev_project/prepare/registry.py`](../../dev_project/prepare/registry.py)). Цель — **ясность границ**, а не полное разрезание всех связей.

## Зоны

| Зона | Шаги (id) | Что делает |
|------|-----------|------------|
| Git и исходники | `git.lock_load`, `git.ensure_present`, `git.materialize_developing`, `git.materialize_platform`, `sources.materialize` | Загрузка фиксации версий; проверка деревьев при `--no-git-update`; клон проекта разработки, затем платформы Odoo; служебные исходники |
| Скрипты после клонирования | `hooks.post_clone` | Хуки манифеста после клонов платформы/проекта |
| Зависимости | `git.materialize_dependencies` | Разрешение графа и клон/обновление репозиториев зависимостей |
| Карта проекта | `project.map_folders` | Карта путей и томов Docker **без** клона и без обхода OCA; в `prepare` ей предшествует `git.materialize_dependencies` |
| Фиксация версий (пины) | `git.lock_apply` | Применить пины из lock/манифеста до checkout |
| Шаблоны и compose | `template.*`, `docker.*`, `database.drift`, `compose.*` (кроме runtime `compose.up`) | Dockerfile, odoo.conf, фрагменты, генерация и проверка compose |
| Секреты | `secrets.fetch`, `secrets.materialize` | Подтянуть и записать секреты на диск |
| Checkout и ссылки | `git.checkout`, `git.lock_collect`, `git.lock_verify`, `project.update_links` | Переключить коммиты; собрать/проверить lock; мягкие ссылки в проекте |

В таблице `odpm plan` те же зоны показаны заголовками групп (только подписи; id и порядок реестра не меняются).

## Порядок клонов (инвариант)

1. Проект разработки (`git.materialize_developing`)
2. Платформа Odoo (`git.materialize_platform`)
3. … служебные исходники и хуки …
4. Зависимости (`git.materialize_dependencies`)
5. Карта папок (`project.map_folders`) — только тома/пути по уже разрешённому списку (без клона; прямой вызов без шага зависимостей берёт seed-URL из манифеста)

## Обеспечение слоя образа

`odpm image … ensure` **намеренно** запускает узкую подготовку (исходники + секреты по [`IMAGE_ENSURE_STEP_IDS`](../../dev_project/prepare/sources_only.py)), затем сборку слоя. Это контракт [ADR-027](adr-027-layered-ci-images.md): образ без слепка исходников на диске не собирается. В `odpm plan` шаги подготовки и шаги слоёв (`image.*`) помечены разными группами («подготовка» / «сборка образа»).

Полный compose и шаблоны Dockerfile/odoo.conf в этот прогон **не** входят; для `options` в runtime config слоя app builder вызывает генерацию конфига отдельно (см. ADR-027).

## Связанные документы

- [ADR-027](adr-027-layered-ci-images.md) — слои CI-образа и сцепка ensure ↔ узкая подготовка
- [ADR-028](adr-028-git-worktree-tenants.md) — рабочие деревья git по каталогу-тенанту
- [Движок запуска стека](runtime-backend.md) / [ADR-029](adr-029-runtime-backend.md) — шаги после prepare (`runtime.ensure_base`, `compose.up`)
- [Зоны Config](config-zones.md) / [ADR-030](adr-030-config-as-assembler.md) — снимок проекта и порты, не «весь Config»
- [cli-architecture.md](cli-architecture.md) — как добавлять команды
