# CI и workflows

Badges в README указывают на [ci.yml](https://github.com/aayartsev/odpm/actions/workflows/ci.yml) и [ci-docker.yml](https://github.com/aayartsev/odpm/actions/workflows/ci-docker.yml).

## Матрица jobs

| Job | Workflow | Триггер | Gate |
|-----|----------|---------|------|
| **lint** | `ci.yml` | push/PR | рекомендуется обязательный |
| **unit** | `ci.yml` | push/PR, Python 3.10 + 3.12 | рекомендуется обязательный |
| **release-packages** | `release-packages.yml` | push `4.0-beta`/`4.0-rc1`/`main`, tag `v*`, dispatch | артефакт; Release на tag |
| **compose-smoke** | `ci-docker.yml` | push/PR | рекомендуется обязательный |
| **golden-path** | `ci-docker.yml` | nightly, dispatch, label `run-docker` | opt-in |
| **golden-path (pre-release gate)** | `release-packages.yml` | tag `v*-beta`, `v*-rc*`, `v*-alpha` | **обязателен** перед publish |

## Локально

```bash
./scripts/run_compose_smoke_test.sh
ODPM_GOLDEN_PATH_PROJECT=/path/to/project ./scripts/run_golden_path_test.sh
```

## Golden-path secrets

| Имя | Тип | Назначение |
|-----|-----|------------|
| `ODPM_GOLDEN_PATH_ENABLED` | variable | `true` — включить job |
| `ODPM_GOLDEN_PATH_PROJECT` | secret | Путь к odpm-проекту на self-hosted runner |

Label PR `run-docker`: добавить label, **перезапустить** workflow CI Docker.

Self-hosted runner: labels `self-hosted`, `Linux`, `X64`.

### Pre-release golden-path gate

На pre-release тегах (`v*-beta`, `v*-rc*`, `v*-alpha`) job **golden-path** в `release-packages.yml`:

1. ставит **собранный .deb** с этого тега;
2. проверяет `odpm --version`;
3. гоняет `tests.integration.test_golden_path` на `ODPM_GOLDEN_PATH_PROJECT`.

Пока job красный, **publish** / PyPI / Pages **не стартуют**. Требуются `ODPM_GOLDEN_PATH_ENABLED=true` и secret `ODPM_GOLDEN_PATH_PROJECT` (иначе workflow падает явно, без ложного зелёного).

## Branch protection

Рекомендуется: обязательные **lint**, **unit**, **compose-smoke** на `4.0-beta` / `main`.
