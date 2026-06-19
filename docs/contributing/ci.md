# CI и workflows

Badges в README указывают на [ci.yml](https://github.com/aayartsev/odpm/actions/workflows/ci.yml) и [ci-docker.yml](https://github.com/aayartsev/odpm/actions/workflows/ci-docker.yml).

## Матрица jobs

| Job | Workflow | Триггер | Gate |
|-----|----------|---------|------|
| **lint** | `ci.yml` | push/PR | рекомендуется обязательный |
| **unit** | `ci.yml` | push/PR, Python 3.10 + 3.12 | рекомендуется обязательный |
| **release-packages** | `release-packages.yml` | push `4.0-beta`/`4.0-rc1`/`main`, tag `v*`, dispatch | артефакт; Release на tag |
| **compose-smoke** | `ci-docker.yml` | push/PR | рекомендуется обязательный |
| **compose-smoke-mailpit** | `ci-docker.yml` | push/PR (`ODPM_COMPOSE_SMOKE_MAILPIT=1`) | рекомендуется обязательный |
| **golden-path** | `ci-docker.yml` | nightly, dispatch, label `run-docker` | opt-in |

## Локально

```bash
./scripts/run_compose_smoke_test.sh
ODPM_COMPOSE_SMOKE_MAILPIT=1 ./scripts/run_compose_smoke_test.sh
ODPM_GOLDEN_PATH_PROJECT=/path/to/project ./scripts/run_golden_path_test.sh
```

## Golden-path: opt-in и критерии перехода на mandatory

Сейчас **full golden-path** (`init` → `docker compose up` → HTTP 200) остаётся **opt-in**: nightly, `workflow_dispatch`, label PR `run-docker`, self-hosted runner + `ODPM_GOLDEN_PATH_ENABLED` + secret `ODPM_GOLDEN_PATH_PROJECT`.

**Обязательный PR gate** — `compose-smoke` (v1 flat fixture) и **compose-smoke-mailpit** (manifest v2 + `services.mailpit`, `ODPM_COMPOSE_SMOKE_MAILPIT=1`).

Переход golden-path в mandatory gate на `main` / `4.4-dev` — **post-4.4 backlog**, когда выполнены критерии:

| Критерий | Зачем |
|----------|--------|
| Стабильный пул self-hosted runners (labels `self-hosted`, `Linux`, `X64`) | Без очереди и ручного перезапуска |
| Медиана runtime job &lt; 25 мин, flake rate &lt; 5% за 2 недели | Не блокировать merge из-за инфраструктуры |
| Секрет `ODPM_GOLDEN_PATH_PROJECT` и variable `ODPM_GOLDEN_PATH_ENABLED` настроены в org/repo | Job не «ложно зелёный» из-за skip |
| Документированный runbook в [smoke-4.0-checklist.md](../smoke-4.0-checklist.md) | On-call знает, как чинить падения |

До выполнения критериев достаточно **compose-smoke** + unit/contract на каждый PR.

## Golden-path secrets

| Имя | Тип | Назначение |
|-----|-----|------------|
| `ODPM_GOLDEN_PATH_ENABLED` | variable | `true` — включить job |
| `ODPM_GOLDEN_PATH_PROJECT` | secret | Путь к odpm-проекту на self-hosted runner |

Label PR `run-docker`: добавить label, **перезапустить** workflow CI Docker.

Self-hosted runner: labels `self-hosted`, `Linux`, `X64`.

## Branch protection

Рекомендуется: обязательные **lint**, **unit**, **compose-smoke** на `4.0-beta` / `main`.
