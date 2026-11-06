# Сценарий непрерывной интеграции (`ci`)

Переменная **`ODPM_SCENARIO=ci`** — подготовка **готового Docker-образа** проекта: исходники платформы, дополнения, окружение Python и конфигурация **встроены в образ**, каталоги Odoo **не подключаются** с диска машины сборки.

## Назначение

Инженер сборки или конвейер автоматизации получает **воспроизводимый артефакт**: один и тот же код и те же зафиксированные ревизии git, что описаны в `odpm.json` и `.odpm/deps.lock.json`. После сборки образ можно публиковать в реестр и разворачивать на стендах теми средствами, которые уже приняты в организации.

odpm **не заменяет** GitHub Actions, GitLab CI или оркестраторы — он даёт **команду сборки образа** и согласованный способ запуска Odoo с теми же параметрами, что у разработчика и администратора.

## Поведение окружения

| Область | Как устроено |
|---------|--------------|
| **Образ** | Слоистая сборка (ADR-027): `odpm prepare --stop-after sources` → анализ miss → `odpm image <слой> ensure` или ярлык `odpm build` (base → platform → deps? → app). Доступно **только** в этом сценарии. Бэкенд: `docker` / `kaniko` — [ADR-016](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-016-ci-image-build-backends.md). |
| **Семейства слоёв** | Теги registry: **dev** ↔ профиль base `full` (браузер); **runtime** ↔ `medium` (wkhtml, без браузера). Задаётся `ODPM_BASE_IMAGE_PROFILE`. Сценарий `ci` и профиль `ci` **не** переименовываются. |
| **Исходники** | Сначала слепок на хосте (`--stop-after sources`); в финальном образе — без mount с хоста. |
| **Окружение Python** | Bake venv в слое **platform**, не в app. |
| **Отладчик** | Нет. |
| **Секреты модулей** | Mount `.odpm/secrets.json` с хоста **отключён**. Секреты приложения в CI-образ этим механизмом не попадают — см. [локальные секреты](../operations/secrets.md) (TD-FEAT-09). |
| **Фиксация версий** | Строгая проверка `.odpm/deps.lock.json`; несовместимости версий во вложенных описаниях — **ошибка**. |
| **Base image** | По умолчанию профиль **ci** (slim Dockerfile): без Chromium/Xvfb/IDE; отдельный тег `odoo-…-ci`; пересборка при смене шаблона или `Dockerfile` — см. [ADR-007](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-007-base-image-profiles.md). Override: `ODPM_BASE_IMAGE_PROFILE` = `full` / `medium` / `ci`. Для `kaniko` base собирается и **пушится** в `ODPM_BASE_IMAGE_REGISTRY` (ADR-019); final `FROM` использует registry ref. Existence для kaniko — local identity stamp (не probe registry); при stale registry удалите `.odpm/base_image_identity.json` и пересоберите. |

## Типичный конвейер

```text
отправка в git → машина сборки
  → ODPM_SCENARIO=ci
  → ODPM_BASE_IMAGE_PROFILE=full   # семейство dev; или medium → runtime
  → odpm prepare --stop-after sources
  → odpm plan                      # отпечатки / hit-miss слоёв
  → odpm image base ensure
  → odpm image platform ensure
  → odpm image deps ensure         # noop, если нет dependencies
  → odpm image app ensure --image-tag реестр/проект:метка [--image-push]
  # либо ярлык:
  → odpm build [--image-tag …] [--image-builder docker|kaniko] [--image-push]
  → опционально: odpm image lint ensure   # bake кэша хуков pre-commit (нужна сеть)
  → развёртывание (ваши инструменты)
```

`odpm image lint ensure` собирает слой от platform и **прогревает кэш хуков** (`pre-commit install-hooks` внутри образа, кэш в домашнем каталоге пользователя контейнера). Git для bake идёт в изолированном каталоге `.odpm-lint-bake`, не в корне home поверх platform. Полный `pre-commit run --all-files` по коду заявки в bake не входит — код подставляют позже в задании. Для cold ensure builder должен иметь сеть (клонирование репозиториев хуков).

`odpm image … ensure` сначала выполняет **узкую подготовку** (исходники + секреты по списку разрешённых шагов; полный compose и шаблоны Dockerfile/odoo.conf не входят), затем **сборку слоя**. Эта сцепка намеренная (ADR-027): без слепка исходников на диске слой не собирается. В `odpm plan` группы шагов подготовки и шаги `image.*` подписаны отдельно. Команда не запускает шаг `template.odoo_conf`, но перед записью контекста сборки вызывает `generate_odoo_conf_docker_data` (после обновления секретов и перезагрузки манифеста). Слой **app** обязан нести в `/run/odpm/config.json` секцию `odoo_config_data.options` (в т.ч. `db_*` из effective `ci` с раскрытыми `${@secret:…}`).

Видимые шаги git в prepare разделены: проект разработки → платформа → зависимости; карта папок (`project.map_folders`) не клонирует и не обходит OCA (только тома по уже разрешённому списку). Карта зон: [prepare-zones.md](https://github.com/aayartsev/odpm/blob/4.8.0-dev/docs/contributing/prepare-zones.md).

Для проверки наличия слоёв в remote registry нужен **`crane digest`** (иначе fail-fast). Для публикации alias publish-тега после kaniko (`--image-push` / `ODPM_CI_IMAGE_PUSH`, когда fingerprint-cache не в локальном Docker) нужен **`crane copy`**. Принудительная пересборка текущего слоя: `ODPM_IMAGE_FORCE_REBUILD=1`. Опциональная очистка устаревших `cache-*` того же слоя после успешного ensure: `ODPM_IMAGE_PRUNE_STALE=1` или `--image-prune-stale` (оставляет тег с текущим отпечатком; плавающие `mr-*` / publish-тег не трогает; без crane очистка remote — мягкий сбой с логом).

Параллельные слепки (каталог на MR) на одном томе `ODOO_PROJECTS_DIR`: `ODPM_GIT_WORKTREE=1` или `--git-worktree` — общее bare-зеркало и отдельное worktree на тенант (`basename` каталога проекта), без драки за один checkout. Подробнее: [ADR-028](https://github.com/aayartsev/odpm/blob/4.8.0-dev/docs/contributing/adr-028-git-worktree-tenants.md).

## Чеклист

1. В git: `odpm.json` и закоммиченный `.odpm/deps.lock.json`.
2. На машине сборки: odpm, `.env` с `ODPM_SCENARIO=ci`; для `docker` — Docker daemon; для `kaniko` — executor (`docker-run` или `direct`) и pullable base из registry.
3. Перед слиянием: `odpm plan --strict` — код возврата 1 при неожиданных изменениях.
4. Проверка: HTTP-ответ 200 на `/web` после `docker compose up`.

## Примеры команд

```bash
# ~/.odpm/.env (daemonless)
# ODPM_SCENARIO=ci
# ODOO_PROJECTS_DIR=/data/odoo_projects
# ODPM_CI_IMAGE_BUILDER=kaniko
# ODPM_KANIKO_EXECUTOR_MODE=direct
# ODPM_BASE_IMAGE_REGISTRY=registry.example.com/odpm
# ODPM_CI_IMAGE_PUSH=1

export ODPM_SCENARIO=ci
export ODPM_BASE_IMAGE_PROFILE=full   # семейство dev
odpm prepare --stop-after sources
odpm plan
odpm image platform ensure
odpm image app ensure --image-tag myregistry/client-odoo:19.0 --image-push
# ярлык всей цепочки без lint:
odpm build --image-tag myregistry/client-odoo:19.0
odpm build --image-builder kaniko --image-tag myregistry/client-odoo:19.0 --image-push
ODPM_IMAGE_PRUNE_STALE=1 odpm image app ensure --image-tag myregistry/client-odoo:19.0 --image-push
odpm build --image-tag myregistry/client-odoo:19.0 --image-prune-stale
ODPM_CI_IMAGE_BUILDER=kaniko ODPM_KANIKO_EXECUTOR_MODE=direct \
  ODPM_BASE_IMAGE_REGISTRY=registry.example.com/odpm \
  odpm build --image-tag myregistry/client-odoo:19.0 --image-push
docker compose up -d
# Module install after stack is up (bare `odpm up -d/-i` / legacy root flags is rejected in ci).
# Physical odoo key from docker-compose.yml (odoo / acme-odoo / odoo-dev / …):
ODOO_SVC=odoo
docker compose exec "$ODOO_SVC" odoo-bin -d test_db -i base --stop-after-init
```

В сценарии `ci` запрещены `odpm up`, `scaffold` и стековые `database backup|restore|drop|list`. Разрешены `prepare` / `build` / **`image`** / `init` / `plan` / `manifest` / `modules` / `run` / host-`database` / `--version`/`-V` (и legacy-синонимы) — см. [ADR-017](https://github.com/aayartsev/odpm/blob/4.8.0-dev/docs/contributing/adr-017-ci-prepare-only-policy.md), [ADR-026](https://github.com/aayartsev/odpm/blob/4.8.0-dev/docs/contributing/adr-026-cli-command-verbs.md), [ADR-027](https://github.com/aayartsev/odpm/blob/4.8.0-dev/docs/contributing/adr-027-layered-ci-images.md).

## Внешняя PostgreSQL в `ci` (ADR-022)

В effective slice `ci` можно задать `db_*` в `odoo_conf.options` (в `developer` / `server` эти ключи по-прежнему запрещены). Credentials лучше через `${@secret:…}`:

```json
"scenarios": {
  "ci": {
    "odoo_conf": {
      "options": {
        "db_host": "10.241.2.102",
        "db_port": 5000,
        "db_user": "${@secret:pg_user}",
        "db_password": "${@secret:pg_user_password}",
        "proxy_mode": "True",
        "server_wide_modules": "base,web,queue_job"
      }
    }
  }
}
```

Значения попадают в `odoo_config_data` через обычный merge (disk → manifest), в том числе при сборке app-образа через `image app ensure`. Compose-сервис `db` не удаляется; host-side `odpm database` / `ensure_app_role` остаются привязаны к compose postgres. См. [odoo.conf](../reference/odoo-conf.md), [ADR-022](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-022-odoo-conf-scenario-frozen.md).

Без `--image-push` бэкенд `kaniko` пишет tar в `.odpm/ci-build-context/odpm-ci-image.tar`.

В режиме `docker-run` с `--image-push` нужен `~/.docker/config.json` (`docker login`); иначе odpm завершится с ошибкой до запуска executor. Образ executor по умолчанию закреплён (`gcr.io/kaniko-project/executor:v1.23.2`); перекрывается `ODPM_KANIKO_EXECUTOR_IMAGE`. Opt-in Docker integration в CI покрывает только бэкенд `docker`; argv/`direct` для `kaniko` — unit-тесты.

Для **`direct`** под **non-root** пользователем сборки: odpm не работает от root, но Kaniko executor часто требует привилегий. Задайте **`ODPM_KANIKO_EXECUTOR_WRAPPER`** — скрипт, запускающий executor от root (рекомендуется), или **`ODPM_KANIKO_EXECUTOR_SUDO=1`** с passwordless sudo для бинаря executor. Опционально **`ODPM_KANIKO_EXECUTOR_EXTRA_FLAGS`** (напр. `--kaniko-dir=/tmp/kaniko`) для путей runtime Kaniko. См. [ADR-016](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-016-ci-image-build-backends.md).

Инициализация без диалогов:

```bash
export ODPM_SCENARIO=ci
export ODOO_PROJECTS_DIR=/data/odoo_projects
export BACKUP_DIR=/data/backups
# init без compose up (4.8: legacy-комбо; иначе odpm init поднимает стек)
odpm --init https://github.com/example/demo.git --skip-start
```

См. [запуск без диалогов](../operations/non-interactive.md).
