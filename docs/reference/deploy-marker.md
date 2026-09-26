# Маркер деплоя модулей

Файл **`.odpm/deploy/last_applied.json`** хранит SHA developing-репозитория, на котором последний раз успешно применили `-i`/`-u`. Это **не** часть `odpm.json` и не lock зависимостей.

## Расположение

| Путь | Назначение |
|------|------------|
| `{project_dir}/.odpm/deploy/last_applied.json` | Маркер на **хосте проекта odpm** (каталог с `docker-compose.yml`), не обязательно корень git developing |
| `.odpm/.gitignore` → `deploy/` | Пишется при первом `record-applied` / использовании маркера |

Поля JSON:

```json
{
  "developing_sha": "abc123…",
  "applied_at": "2026-09-27T10:00:00Z"
}
```

`db_name` в маркере нет: один SHA на инстанс проекта.

## Подкоманды

```bash
odpm modules diff
odpm modules diff --diff-base @last-applied --format shell
odpm modules diff --diff-base origin/main --format json
odpm modules record-applied
```

| Команда | Описание |
|---------|----------|
| `modules diff` | Списки init/update по `git diff BASE...HEAD` в developing |
| `modules record-applied` | Записать HEAD developing в маркер (без compose) |

Форматы `--format`: **`text`** (по умолчанию), **`shell`** (`export ODPM_INIT_MODULES=…` / `ODPM_UPDATE_MODULES=…`), **`json`**. Списки идут в **stdout**; логи — в stderr/logger, чтобы `eval "$(…)"` оставался чистым.

## Baseline

Приоритет, если `--diff-base` не указан:

1. `ODPM_DIFF_BASE`
2. `CI_MERGE_REQUEST_DIFF_BASE_SHA` (GitLab MR)
3. SHA из маркера, если файл есть
4. иначе **ошибка** — без baseline списки не выдумываются

`--diff-base @last-applied` принудительно читает маркер (ошибка, если файла нет). Первый деплой: передайте явный `--diff-base <sha|tag>` (или env), примените модули, затем `record-applied`.

Репозиторий: только **developing** checkout с `.git`. Удалённые модули игнорируются; rename → новый путь как init, если модуля не было на BASE.

## Рецепт apply (shell)

Пустые списки **не** передавайте как `-i ""` / `-u ""` — CLI отвергает пустой CSV.

```bash
eval "$(odpm modules diff --diff-base @last-applied --format shell)"

args=(-d prod_db)
[[ -n "${ODPM_INIT_MODULES}" ]] && args+=(-i "${ODPM_INIT_MODULES}")
[[ -n "${ODPM_UPDATE_MODULES}" ]] && args+=(-u "${ODPM_UPDATE_MODULES}")
odpm "${args[@]}" --odoo-bin --stop-after-init

# только после exit 0
odpm modules record-applied
```

Долгоживущий `docker compose up` **без** `--stop-after-init` не подходит для автообновления маркера: маркер обновляйте вручную/`record-applied` после успешного apply.

## CI / MR

В pipeline задайте baseline через `--diff-base` или `CI_MERGE_REQUEST_DIFF_BASE_SHA` / `ODPM_DIFF_BASE`. Подкоманда `modules` входит в CI allowlist (как `plan` / `database` / `manifest`).

## Вне scope v1

Нет одноразового `--modules-from-git-diff` оркестратора и нет общего `odpm run` / recipes framework — только подкоманды и документированный shell-рецепт.
