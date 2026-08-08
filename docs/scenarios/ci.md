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
| **Base image** | Профиль **ci** (slim Dockerfile): без Chromium/Xvfb/IDE; отдельный тег `odoo-…-ci`; пересборка при смене шаблона или `Dockerfile` — см. [ADR-007](https://github.com/aayartsev/odpm/blob/4.6.0-dev/docs/contributing/adr-007-base-image-profiles.md). Для бэкенда `kaniko` локальный ensure base **не** выполняется: тег base должен быть доступен из registry. |

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
export ODPM_SCENARIO=ci
odpm --skip-start
odpm --build-image --image-tag myregistry/client-odoo:19.0
odpm --build-image --image-builder kaniko --image-tag myregistry/client-odoo:19.0 --image-push
ODPM_CI_IMAGE_BUILDER=kaniko ODPM_KANIKO_EXECUTOR_MODE=direct \
  odpm --build-image --image-tag myregistry/client-odoo:19.0 --image-push
docker compose up -d
odpm -d test_db -i --odoo-bin --stop-after-init
```

Без `--image-push` бэкенд `kaniko` пишет tar в `.odpm/ci-build-context/odpm-ci-image.tar`.

В режиме `docker-run` с `--image-push` нужен `~/.docker/config.json` (`docker login`); иначе odpm завершится с ошибкой до запуска executor. Образ executor по умолчанию закреплён (`gcr.io/kaniko-project/executor:v1.23.2`); перекрывается `ODPM_KANIKO_EXECUTOR_IMAGE`. Opt-in Docker integration в CI покрывает только бэкенд `docker`; argv/`direct` для `kaniko` — unit-тесты.

Инициализация без диалогов:

```bash
export ODPM_SCENARIO=ci
export ODOO_PROJECTS_DIR=/data/odoo_projects
export BACKUP_DIR=/data/backups
odpm --init https://github.com/example/demo.git --skip-start
```

См. [запуск без диалогов](../operations/non-interactive.md).
