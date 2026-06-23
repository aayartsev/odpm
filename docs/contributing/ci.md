# CI и workflows

Badges в README указывают на [ci.yml](https://github.com/aayartsev/odpm/actions/workflows/ci.yml) и [ci-docker.yml](https://github.com/aayartsev/odpm/actions/workflows/ci-docker.yml).

**Активная ветка разработки 4.5:** `4.5-dev` (push/PR → lint, unit, contract, compose-smoke, deploy `/dev/` docs).

## Матрица jobs

| Job | Workflow | Триггер | Gate |
|-----|----------|---------|------|
| **lint** | `ci.yml` | push/PR | рекомендуется обязательный |
| **i18n** | `ci.yml` | push/PR | **обязательный** (4.5) — `check_i18n_catalog.py` |
| **unit** | `ci.yml` | push/PR, Python 3.10 + 3.12 | рекомендуется обязательный |
| **release-packages** | `release-packages.yml` | push `4.0-beta`/`4.0-rc1`/`main`, tag `v*`, dispatch | артефакт; Release на tag |
| **contract** | `ci.yml` | push/PR | рекомендуется обязательный |
| **compose-smoke** | `ci-docker.yml` | push/PR | **обязательный** (T1); v1 fixture + Mailpit manifest (`ODPM_COMPOSE_SMOKE_MAILPIT=1`) |
| **http-smoke** | `ci-docker.yml` | push/PR | **обязательный** (T2, 4.5); in-repo fixture, Mailpit `compose up`, HTTP 200 — [ADR-006](adr-006-integration-gate-policy.md) |
| **golden-path** | `ci-docker.yml` | nightly, dispatch, label `run-docker` | opt-in (T3) |
| **golden-path (pre-release gate)** | `release-packages.yml` | tag `v*-beta`, `v*-rc*`, `v*-alpha` | **обязателен** перед publish |
| **fixture-golden-path** | `ci-integration-weekly.yml` | weekly, dispatch | I2 — in-repo `/web` |
| **ci-image-build** | `ci-integration-weekly.yml` | weekly, dispatch | I2 — `test_ci_image_build` |
| **deb-smoke** | `ci-integration-weekly.yml` | weekly, dispatch | I2 — `build_deb.sh` + install smoke |

Подробнее: [ADR-006 Integration gate](adr-006-integration-gate-policy.md).

## Локально

```bash
./scripts/run_compose_smoke_test.sh
ODPM_COMPOSE_SMOKE_MAILPIT=1 ./scripts/run_compose_smoke_mailpit_test.sh
./scripts/run_compose_smoke_extended_test.sh   # plugin + hooks E2E
./scripts/run_http_smoke_test.sh
./scripts/run_fixture_golden_path_test.sh      # weekly matrix
ODPM_GOLDEN_PATH_PROJECT=/path/to/project ./scripts/run_golden_path_test.sh
```

### Переменные integration (parity с CI)

| Переменная | Значение по умолчанию | Job |
|------------|----------------------|-----|
| `ODPM_COMPOSE_SMOKE_TIMEOUT` | `900` | compose-smoke |
| `ODPM_HTTP_SMOKE_TIMEOUT` | `600` | http-smoke |
| `ODPM_GOLDEN_PATH_TIMEOUT` | `900` (локально), `2400` (CI golden-path) | golden-path |
| `ODPM_FIXTURE_GOLDEN_TIMEOUT` | `900` | fixture-golden-path |
| `ODPM_COMPOSE_DEBUG_DIR` | пусто | при ошибке — каталог debug bundle |

## Flakes и артефакты (I3)

- Повтор: re-run failed job в GitHub Actions (один раз); локально — `docker compose down` в fixture/project, затем повтор скрипта.
- `docker pull` / registry: подождать 5–10 минут, re-run.
- При падении `http-smoke` / `golden-path` CI загружает artifact `*-compose-logs` (compose service logs + `docker-compose.yml`).

## Golden-path secrets

| Имя | Тип | Назначение |
|-----|-----|------------|
| `ODPM_GOLDEN_PATH_ENABLED` | variable | `true` — включить job |
| `ODPM_GOLDEN_PATH_PROJECT` | secret | Путь к odpm-проекту на self-hosted runner |

Label PR `run-docker`: добавить label, **перезапустить** workflow CI Docker.

Self-hosted runner: labels `self-hosted`, `Linux`, `X64`.

### Pre-release golden-path gate

На pre-release тегах (`v*-beta`, `v*-rc*`, `v*-alpha`) job **golden-path** в `release-packages.yml`:

1. проверяет **собранный .deb** в чистом `ubuntu:24.04` (Docker, без `sudo` на runner);
2. проверяет `odpm --version` внутри контейнера;
3. гоняет `tests.integration.test_golden_path` на `ODPM_GOLDEN_PATH_PROJECT`.

Пока job красный, **publish** / PyPI / Pages **не стартуют**. Требуются `ODPM_GOLDEN_PATH_ENABLED=true` и secret `ODPM_GOLDEN_PATH_PROJECT` (иначе workflow падает явно, без ложного зелёного).

## Branch protection

Рекомендуется обязательные checks на PR:

| Ветка | Required checks |
|-------|-----------------|
| `4.5-dev` | **lint**, **unit**, **contract**, **i18n**, **compose-smoke**, **http-smoke** |
| `4.4-dev`, `4.0-beta`, `main` | то же (если ветка ещё принимает PR) |

Настройка: GitHub → Settings → Branches → rule для `4.5-dev` → Require status checks.

```bash
# Пример (нужны права admin; имена checks — как в UI Actions после первого green run):
gh api repos/{owner}/{repo}/branches/4.5-dev/protection -X PUT \
  -f required_status_checks='{"strict":true,"contexts":["lint","unit","contract","i18n","compose-smoke","http-smoke"]}' \
  -f enforce_admins=false \
  -f required_pull_request_reviews='{"required_approving_review_count":0}' \
  -f restrictions=null
```
