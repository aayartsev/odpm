# Сценарий непрерывной интеграции (`ci`)

Переменная **`ODPM_SCENARIO=ci`** — подготовка **готового Docker-образа** проекта: исходники платформы, дополнения, окружение Python и конфигурация **встроены в образ**, каталоги Odoo **не подключаются** с диска машины сборки.

## Назначение

Инженер сборки или конвейер автоматизации получает **воспроизводимый артефакт**: один и тот же код и те же зафиксированные ревизии git, что описаны в `odpm.json` и `.odpm/deps.lock.json`. После сборки образ можно публиковать в реестр и разворачивать на стендах теми средствами, которые уже приняты в организации.

odpm **не заменяет** GitHub Actions, GitLab CI или оркестраторы — он даёт **команду сборки образа** и согласованный способ запуска Odoo с теми же параметрами, что у разработчика и администратора.

## Поведение окружения

| Область | Как устроено |
|---------|--------------|
| **Образ** | Создаётся командой `odpm --build-image` (доступна **только** в этом сценарии). Бэкенд: `docker` (по умолчанию) или `kaniko` — см. [ADR-016](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-016-ci-image-build-backends.md). |
| **Исходники** | Внутри образа, без подключения с хоста. |
| **Окружение Python** | Собрано при сборке образа, не пересоздаётся при каждом `up`. |
| **Отладчик** | Нет. |
| **Секреты модулей** | Mount `.odpm/secrets.json` с хоста **отключён**. Секреты приложения в CI-образ этим механизмом не попадают — см. [локальные секреты](../operations/secrets.md) (TD-FEAT-09). |
| **Фиксация версий** | Строгая проверка `.odpm/deps.lock.json`; несовместимости версий во вложенных описаниях — **ошибка**. |
| **Base image** | Профиль **ci** (slim Dockerfile): без Chromium/Xvfb/IDE; отдельный тег `odoo-…-ci`; пересборка при смене шаблона или `Dockerfile` — см. [ADR-007](https://github.com/aayartsev/odpm/blob/4.6.0-dev/docs/contributing/adr-007-base-image-profiles.md). Для `kaniko` base собирается и **пушится** в `ODPM_BASE_IMAGE_REGISTRY` (ADR-019); final `FROM` использует registry ref. Existence для kaniko — local identity stamp (не probe registry); при stale registry удалите `.odpm/base_image_identity.json` и пересоберите. |

## Типичный конвейер

```text
отправка в git → машина сборки
  → ODPM_SCENARIO=ci
  → odpm --skip-start
  → odpm --build-image [--image-tag реестр/проект:метка] [--image-builder docker|kaniko] [--image-push]
  → публикация образа (или --image-push / артефакт tar для kaniko)
  → развёртывание (ваши инструменты)
```

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
odpm --skip-start
odpm --build-image --image-tag myregistry/client-odoo:19.0
odpm --build-image --image-builder kaniko --image-tag myregistry/client-odoo:19.0 --image-push
ODPM_CI_IMAGE_BUILDER=kaniko ODPM_KANIKO_EXECUTOR_MODE=direct \
  ODPM_BASE_IMAGE_REGISTRY=registry.example.com/odpm \
  odpm --build-image --image-tag myregistry/client-odoo:19.0 --image-push
docker compose up -d
# Module install after stack is up (bare odpm -d/-i is rejected in ci).
# Service key is "odoo" unless ODPM_COMPOSE_PREFIX is set (then "{prefix}odoo"):
ODOO_SVC="${ODPM_COMPOSE_PREFIX:-}odoo"
docker compose exec "$ODOO_SVC" odoo-bin -d test_db -i base --stop-after-init
```

В сценарии `ci` bare `odpm` без `--skip-start` / `--build-image` (и без allowlist: `plan`, `manifest`, `database`, `--update-lock`, `--init`, …) завершается ошибкой — см. [ADR-017](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-017-ci-prepare-only-policy.md).

Без `--image-push` бэкенд `kaniko` пишет tar в `.odpm/ci-build-context/odpm-ci-image.tar`.

В режиме `docker-run` с `--image-push` нужен `~/.docker/config.json` (`docker login`); иначе odpm завершится с ошибкой до запуска executor. Образ executor по умолчанию закреплён (`gcr.io/kaniko-project/executor:v1.23.2`); перекрывается `ODPM_KANIKO_EXECUTOR_IMAGE`. Opt-in Docker integration в CI покрывает только бэкенд `docker`; argv/`direct` для `kaniko` — unit-тесты.

Для **`direct`** под **non-root** пользователем сборки: odpm не работает от root, но Kaniko executor часто требует привилегий. Задайте **`ODPM_KANIKO_EXECUTOR_WRAPPER`** — скрипт, запускающий executor от root (рекомендуется), или **`ODPM_KANIKO_EXECUTOR_SUDO=1`** с passwordless sudo для бинаря executor. Опционально **`ODPM_KANIKO_EXECUTOR_EXTRA_FLAGS`** (напр. `--kaniko-dir=/tmp/kaniko`) для путей runtime Kaniko. См. [ADR-016](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-016-ci-image-build-backends.md).

Инициализация без диалогов:

```bash
export ODPM_SCENARIO=ci
export ODOO_PROJECTS_DIR=/data/odoo_projects
export BACKUP_DIR=/data/backups
odpm --init https://github.com/example/demo.git --skip-start
```

См. [запуск без диалогов](../operations/non-interactive.md).
