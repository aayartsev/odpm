# CI и workflows

Badges в README указывают на [ci.yml](https://github.com/aayartsev/odpm/actions/workflows/ci.yml) и [ci-docker.yml](https://github.com/aayartsev/odpm/actions/workflows/ci-docker.yml).

**Активная ветка разработки 4.7:** `4.7.0-dev` (push/PR → lint, unit, contract, compose-smoke, deploy `/dev/` docs).

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
| `ODPM_GOLDEN_PATH_TIMEOUT` | `60` | golden-path (HTTP wait; job ≤9 min) |
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

### Обслуживание golden-path проекта (self-hosted)

Проект в `ODPM_GOLDEN_PATH_PROJECT` — **долгоживущее окружение** на runner. CI **не** выполняет `odpm init` перед тестом: job только делает `docker compose up` и ждёт HTTP 200 на `/web`. Новый `.deb` из pre-release тега проверяется отдельным smoke-шагом, но контейнерный venv и клон Odoo остаются на диске runner.

**Когда обновлять проект вручную**

| Событие | Действие |
|---------|----------|
| `git pull` в каталоге Odoo (`requirements.txt` изменился) | На хосте: `odpm` (без `--skip-start`) или `odpm --plan` → ожидается `venv_lock_hash changed` и пересборка venv. С 4.6 хеш `odoo/requirements.txt` входит в `venv_lock_hash`. |
| Смена `python_version` / distro / `odoo_version` в `odpm.json` | То же: `odpm` пересоберёт runtime и venv. |
| Ошибка в логах odoo: `ModuleNotFoundError` (например `decorator`) | С 4.6 odpm ставит `decorator` как implicit-пакет при сборке venv. Если ошибка остаётся после `odpm` — удалить `.venv` и `.lock`, перезапустить `odpm`; для веток Odoo без `decorator` в `requirements.txt` это нормальный путь. |
| HTTP 500 на `/web`, в логах `invalid manifest` / `Invalid version` (модуль проекта, напр. `first_module`) | Исправить `version` в `__manifest__.py` кастомного аддона под правила Odoo 19 (`19.0.1.0`, не `19.0.1.0.0`). Это содержимое `ODPM_GOLDEN_PATH_PROJECT`, не odpm. |
| HTTP 500, в postgres: `translate IS TRUE must be type boolean` / в odoo: `res_lang.short_time_format does not exist` | Несовпадение кода/БД. На Odoo 19 колонка `short_time_format` **удалена** (datetime remake) — отсутствие после свежего init нормально. Ошибка `column … does not exist` при SELECT значит: **на диске старый checkout Odoo**, который ещё объявляет поле, а БД уже от нового дерева. Предпочтительно: `git pull` Odoo 19.0 после remake. Иначе remedi ate БД под текущий код: `ODPM_GOLDEN_PATH_AUTO_REMEDIATE=1 … refresh_golden_path_project.sh`. Preflight / remedi ate: **`base` 19.x + `web`**; колонка `short_time_format` обязательна, если смонтированный `res_lang.py` ещё содержит поле (платформа ищется через `ODOO_PLATFORM_DIR`, `file://` в manifest и bind-volume в `docker-compose.yml`). Если платформу найти нельзя, а колонки нет — remedi ate всё равно. Wipe volume — через `docker run … alpine`. |
| HTTP 500, в odoo: `res.lang` / `_get_data` / `QWebException` на `/web/login` | Часто та же причина: БД или addons не соответствуют Odoo 19 на диске runner. Пересоздать `test_db` как в строке выше; затем `docker compose down` и повторить golden-path. |
| После падения golden-path | `docker compose down` в каталоге проекта; смотреть artifact `golden-path-compose-logs`. HTTP wait: `ODPM_GOLDEN_PATH_TIMEOUT=60` внутри job `timeout-minutes: 9`. |

**Минимальная проверка на runner**

```bash
export PROJECT=/path/from/ODPM_GOLDEN_PATH_PROJECT
cd "$PROJECT"
docker compose down
odpm --plan    # при изменении Odoo/requirements — шаг UPDATE compose.service (venv)
odpm           # materialize без --skip-start при необходимости
ODPM_GOLDEN_PATH_PROJECT="$PROJECT" ./scripts/run_golden_path_test.sh
```

**Проверка venv внутри контейнера** (после `compose up`):

```bash
docker compose exec odoo python3 -c "import decorator, passlib, lxml"
```

Label PR `run-docker`: добавить label, **перезапустить** workflow CI Docker.

Self-hosted runner: labels `self-hosted`, `Linux`, `X64`.

### Self-hosted: узкий NOPASSWD для установки `.deb`

Pre-release golden-path ставит артефактный `.deb` **на хост runner** (`sudo -n /usr/bin/dpkg -i`). Без passwordless sudo шаг **молча зависает** на prompt — поэтому CI сначала проверяет `sudo -n /usr/bin/dpkg --version` и ставит пакет под `timeout 60`. Не использовать `sudo -E`: узкий sudoers без `SETENV` отвечает «не разрешено сохранять окружение».

На машине runner (один раз, от root):

```bash
# от имени пользователя сервиса actions-runner:
id -un
sed "s/RUNNER_USER/$(id -un)/" /path/to/odpm/scripts/ci/github-actions-runner-sudoers.example \
  | sudo tee /etc/sudoers.d/github-actions-runner >/dev/null
sudo chmod 0440 /etc/sudoers.d/github-actions-runner
sudo visudo -cf /etc/sudoers.d/github-actions-runner
sudo -n /usr/bin/dpkg --version   # must print version without password
```

Шаблон: [`scripts/ci/github-actions-runner-sudoers.example`](../../scripts/ci/github-actions-runner-sudoers.example) — только `dpkg` / `apt-get` / `apt`, не `NOPASSWD:ALL`.

### Pre-release golden-path gate

На pre-release тегах (`v*-beta`, `v*-rc*`, `v*-alpha`) job **golden-path** в `release-packages.yml` (`timeout-minutes: 9`):

1. проверяет **собранный .deb** в чистом `ubuntu:24.04` (Docker, без `sudo` на runner);
2. **fail-fast** `sudo -n /usr/bin/dpkg`, затем `timeout 60 sudo -n dpkg -i` + `scripts/refresh_golden_path_project.sh` с **`ODPM_GOLDEN_PATH_AUTO_REMEDIATE=1`** (`odpm --skip-start`; remedi ate **только** при несовместимой схеме);
3. `scripts/preflight_golden_path_project.sh` — fail-fast, если схема всё ещё несовместима с Odoo 19;
4. гоняет `tests.integration.test_golden_path` на `ODPM_GOLDEN_PATH_PROJECT` (`ODPM_GOLDEN_PATH_TIMEOUT=60`).

Remedi ate в gate ограничен несовместимой схемой (не wipe на каждом run). Пока job красный, **publish** / PyPI / Pages **не стартуют**. Требуются `ODPM_GOLDEN_PATH_ENABLED=true` и secret `ODPM_GOLDEN_PATH_PROJECT` (иначе workflow падает явно, без ложного зелёного).

## Branch protection

Рекомендуется обязательные checks на PR:

| Ветка | Required checks |
|-------|-----------------|
| `4.7.0-dev` | **lint**, **unit**, **contract**, **i18n**, **compose-smoke**, **http-smoke** |
| `4.5-dev`, `4.4-dev`, `4.0-beta`, `main` | то же (если ветка ещё принимает PR) |

Настройка: GitHub → Settings → Branches → rule для `4.7.0-dev` → Require status checks.

```bash
# Пример (нужны права admin; имена checks — как в UI Actions после первого green run):
gh api repos/{owner}/{repo}/branches/4.7.0-dev/protection -X PUT \
  -f required_status_checks='{"strict":true,"contexts":["lint","unit","contract","i18n","compose-smoke","http-smoke"]}' \
  -f enforce_admins=false \
  -f required_pull_request_reviews='{"required_approving_review_count":0}' \
  -f restrictions=null
```
