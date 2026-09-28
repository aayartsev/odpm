# Рецепты (`odpm run`)

Слой **рецептов** собирает параметры из CLI/env и выполняет упорядоченные **повторные вызовы odpm** (subprocess), не мутируя флаги текущего запуска.

Предназначение: сценарии вроде «посчитать модули → `-i`/`-u` → записать marker» на **server**. Hooks/plugins остаются in-process и не заменяют этот слой.

## Команды

```bash
odpm run --list
odpm run apply-modules-from-diff -d prod_db
odpm run apply-modules-from-diff -d prod_db --diff-base @last-applied --dry-run
```

| Флаг | Описание |
|------|----------|
| `--list` | Список рецептов (builtin + `.odpm/recipes/*.yaml`) |
| `--dry-run` | Печать плана argv; для `apply-modules-from-diff` всё же выполняется `modules diff` (capture), apply/record не запускаются |
| `-d` | Имя БД (param `database`; иначе env `ODPM_RUN_DATABASE`) |
| `--diff-base` | Baseline для рецептов с `diff_base` |

## Discovery

1. Python builtins (пакет odpm), сейчас: `apply-modules-from-diff`
2. Проект: `{project_dir}/.odpm/recipes/<name>.yaml` — **перекрывает** builtin с тем же именем

Не перекрывайте `apply-modules-from-diff` без необходимости.

## Builtin: `apply-modules-from-diff`

Для **`ODPM_SCENARIO=server`** (и ручного запуска в developer).

1. `odpm modules diff [--diff-base] --format json`
2. Если есть init/update: `odpm -d … [-i …] [-u …] --odoo-bin --stop-after-init`
3. `odpm modules record-applied` (в т.ч. когда оба списка пусты — сдвиг baseline)

Пустые `-i`/`-u` не передаются. Долгоживущий compose без `--stop-after-init` этим рецептом не управляется.

### CI

В `ODPM_SCENARIO=ci` end-to-end apply через `odpm run` **не** поддерживается (дочерний `odpm -d -i/-u` не в CI allowlist). В CI используйте `odpm modules diff`; apply выполняйте на server.

## YAML-рецепты (v1)

Линейные шаги без условий. Подстановки: `${param.name}`, `${env:VAR}`.

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
