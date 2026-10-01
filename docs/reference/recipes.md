# Рецепты (`odpm run`)

Слой **рецептов** собирает параметры из CLI/env и выполняет упорядоченные **повторные вызовы odpm** (subprocess), не мутируя флаги текущего запуска.

Предназначение: сценарии вроде «посчитать модули → `-i`/`-u` → записать marker» на **server**. Hooks/plugins остаются in-process и не заменяют этот слой.

## Команды

```bash
odpm run --list
odpm run apply-modules-from-diff -d prod_db
odpm run apply-modules-from-diff -d prod_db --diff-base @last-applied --dry-run
odpm run pull-remote-db -d local_copy --url https://client.example.com --remote-db prod
```

| Флаг | Описание |
|------|----------|
| `--list` | Список рецептов (builtin + `.odpm/recipes/*.yaml`) |
| `--dry-run` | Печать плана argv; для `apply-modules-from-diff` всё же выполняется `modules diff` (capture), apply/record не запускаются; для `pull-remote-db` сеть **не** вызывается |
| `-d` | Имя БД (param `database`; иначе env `ODPM_RUN_DATABASE`) |
| `--diff-base` | Baseline для рецептов с `diff_base` |
| `--url` | Remote Odoo URL для рецептов с `url` (иначе env `ODPM_REMOTE_DB_URL`) |
| `--remote-db` | Remote DB name для рецептов с `remote_db` (иначе env `ODPM_REMOTE_DB_NAME`) |

## Discovery

1. Python builtins (пакет odpm), сейчас: `apply-modules-from-diff`, `pull-remote-db`
2. Проект: `{project_dir}/.odpm/recipes/<name>.yaml` — **перекрывает** builtin с тем же именем

Не перекрывайте builtin-рецепты без необходимости.

## Builtin: `apply-modules-from-diff`

Для **`ODPM_SCENARIO=server`** (и ручного запуска в developer).

1. `odpm modules diff [--diff-base] --format json`
2. Если есть init/update: `odpm -d … [-i …] [-u …] --odoo-bin --stop-after-init`
3. `odpm modules record-applied` (в т.ч. когда оба списка пусты — сдвиг baseline)

Пустые `-i`/`-u` не передаются. Долгоживущий compose без `--stop-after-init` этим рецептом не управляется.

### CI

В `ODPM_SCENARIO=ci` end-to-end apply через `odpm run` **не** поддерживается (дочерний `odpm -d -i/-u` не в CI allowlist). В CI используйте `odpm modules diff`; apply выполняйте на server.

## Builtin: `pull-remote-db`

Shortcut для **`developer` / `server`**: только **pull + `--db-restore`**. Не ставит модули и не сбрасывает admin-пароль.

```bash
export ODPM_REMOTE_DB_MASTER_PWD='…'   # master password менеджера БД на удалённом инстансе
odpm run pull-remote-db -d local_copy \
  --url https://client.example.com \
  --remote-db prod
```

1. `odpm database pull --url … --remote-db …` → файл в `BACKUP_DIR` (пароль только из env; на stdout — имя архива)
2. `odpm -d … --db-restore <archive>` — полный prepare/runtime, как обычный restore

`--dry-run` печатает argv **без** сети. Не храните master password в git. Для больших дампов timeout HTTP по умолчанию 600s (tool); шаги рецепта без лимита subprocess.

Нужен каталог проекта odpm с настроенным `BACKUP_DIR`. Типичный CI-use-case для pull+restore **не** поддерживается как цель продукта.

## Сборка пайплайна из примитивов (канон)

`odpm database pull` — низкоуровневый шаг: скачал zip и напечатал имя. Дальнейшие шаги (**restore**, `-i`/`-u`, `--set-admin-pass`, …) собирайте в **shell** (или CI job), а не ждите одного «толстого» `odpm run`.

```bash
export ODPM_REMOTE_DB_MASTER_PWD='…'
ARCHIVE=$(odpm database pull \
  --url https://client.example.com \
  --remote-db prod)
odpm -d test_db --db-restore "$ARCHIVE" -i -u --set-admin-pass
```

Эквивалент двумя вызовами, если достаточно builtin restore:

```bash
odpm run pull-remote-db -d test_db --url https://client.example.com --remote-db prod
odpm -d test_db -i -u --set-admin-pass
```

Почему не YAML: v1 подставляет только `${param.*}` / `${env:…}` и **не** умеет передать stdout шага в следующий argv. Для цепочек с именем архива используйте shell (или свой Python-рецепт).

См. также [CLI: `database pull`](cli.md) и [состояние БД](database-state.md).

## YAML-рецепты (v1)

Линейные шаги без условий. Подстановки: `${param.name}`, `${env:VAR}` — **без** захвата stdout предыдущего шага.

```yaml
name: example-backup
description: Backup then skip-start
params:
  database:
    required: true
    env: ODPM_RUN_DATABASE
steps:
  - odpm: ["-d", "${param.database}", "--db-backup"]
  - odpm: ["--skip-start"]
```

Положите файл в `.odpm/recipes/example-backup.yaml`. Шаг не может начинаться с `run` (запрет рекурсии).

## Модель выполнения

Phased: `next_step(ctx)` → subprocess → результат в context → снова `next_step`. У шага: `capture` (для JSON) или live stream; fail-fast при ненулевом exit.
