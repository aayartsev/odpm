# Сценарий непрерывной интеграции (`ci`)

Переменная **`ODPM_SCENARIO=ci`** — подготовка **готового Docker-образа** проекта: исходники платформы, дополнения, окружение Python и конфигурация **встроены в образ**, каталоги Odoo **не подключаются** с диска машины сборки.

## Назначение

Инженер сборки или конвейер автоматизации получает **воспроизводимый артефакт**: один и тот же код и те же зафиксированные ревизии git, что описаны в `odpm.json` и `.odpm/deps.lock.json`. После сборки образ можно публиковать в реестр и разворачивать на стендах теми средствами, которые уже приняты в организации.

odpm **не заменяет** GitHub Actions, GitLab CI или оркестраторы — он даёт **команду сборки образа** и согласованный способ запуска Odoo с теми же параметрами, что у разработчика и администратора.

## Поведение окружения

| Область | Как устроено |
|---------|--------------|
| **Образ** | Создаётся командой `odpm --build-image` (доступна **только** в этом сценарии). |
| **Исходники** | Внутри образа, без подключения с хоста. |
| **Окружение Python** | Собрано при сборке образа, не пересоздаётся при каждом `up`. |
| **Отладчик** | Нет. |
| **Секреты модулей** | Mount с хоста **отключён**. Опционально bake в образ: `ODPM_BAKE_SECRETS=1` при `--build-image` — см. [локальные секреты](../operations/secrets.md), [ADR-002](../contributing/adr-002-ci-secrets-bake.md). |
| **Фиксация версий** | Строгая проверка `.odpm/deps.lock.json`; несовместимости версий во вложенных описаниях — **ошибка**. |

## Типичный конвейер

```text
отправка в git → машина сборки
  → ODPM_SCENARIO=ci
  → odpm --skip-start
  → odpm --build-image [--image-tag реестр/проект:метка]
  → публикация образа
  → развёртывание (ваши инструменты)
```

## Чеклист

1. В git: `odpm.json` и закоммиченный `.odpm/deps.lock.json`.
2. На машине сборки: Docker, odpm, `.env` с `ODPM_SCENARIO=ci`.
3. Перед слиянием: `odpm plan --strict` — код возврата 1 при неожиданных изменениях.
4. Проверка: HTTP-ответ 200 на `/web` после `docker compose up`.

## Примеры команд

```bash
export ODPM_SCENARIO=ci
odpm --skip-start
# optional: odpm --secrets-file /secure/ephemeral.json --skip-start
export ODPM_BAKE_SECRETS=1   # bake module secrets into image when secrets.json exists
odpm --build-image --image-tag myregistry/client-odoo:17.0
docker compose up -d
odpm -d test_db -i --odoo-bin --stop-after-init
```

Инициализация без диалогов:

```bash
export ODPM_SCENARIO=ci
export ODOO_PROJECTS_DIR=/data/odoo_projects
export BACKUP_DIR=/data/backups
odpm --init https://github.com/example/demo.git --skip-start
```

См. [запуск без диалогов](../operations/non-interactive.md).
