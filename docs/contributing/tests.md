# Тесты

Политика «что считать зелёным unit» и эталон Linux CI: [ADR-023](adr-023-local-unit-parity.md). Integration-гейты: [ADR-006](adr-006-integration-gate-policy.md), [ci.md](ci.md).

## Unit

Канон как в CI (`unit` job в [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)):

```bash
cd /path/to/odpm
python3 -m venv .venv-test   # или любой выделенный venv
source .venv-test/bin/activate   # Windows: .venv-test\Scripts\activate
pip install -e ".[test]"
python -m unittest discover -s tests -p 'test_*.py' -q
```

- Python **3.10** и **3.12** (матрица CI).
- Один модуль: `python -m unittest tests.test_odoo_db_ops -v`.
- Без флагов `ODPM_RUN_*` Docker integration в `discover` **пропускаются** (skipped) — для unit-гейта это нормально.
- Extra `.[test]`: сейчас в основном `tomli` на Python до 3.11; ставьте extra всегда, чтобы совпадать с CI.

### Агенты и IDE

- Полный `discover` гоняйте **вне** filesystem/network sandbox IDE (нужны нормальный `PATH`, при необходимости docker/git/gpg и запись в tmp / `.vscode`).
- Unit-сюит обычно укладывается в десятки секунд; держите wall-clock лимит интерактивного прогона порядка **минут** (не часов). Длинные Docker-сценарии — отдельными скриптами ниже, не смешивать с «прогони unit».

## Lint

Scope: `dev_project/`, `tests/`, `odpm.py` — не клиентские addons.

```bash
./scripts/lint.sh
# ruff check dev_project tests odpm.py
```

Pre-commit (опционально):

```bash
pip install pre-commit ruff
pre-commit install
pre-commit run --all-files
```

Правила: `pyproject.toml` `[tool.ruff]`. Включены **E402** и **PLC0415** (импорты наверху модуля, PEP 8); отложенный импорт только с `# noqa: PLC0415  # cycle|optional` — см. `.cursor/rules/python-imports-top-level.mdc`.

## Docker integration (opt-in)

```bash
./scripts/run_compose_smoke_test.sh
ODPM_COMPOSE_SMOKE_MAILPIT=1 ./scripts/run_compose_smoke_mailpit_test.sh
./scripts/run_compose_smoke_extended_test.sh   # plugin + hooks E2E
./scripts/run_http_smoke_test.sh
ODPM_RUN_DOCKER_INTEGRATION=1 python3 -m unittest tests.integration.test_ci_image_build -v
ODPM_GOLDEN_PATH_PROJECT=/path ./scripts/run_golden_path_test.sh
# already refreshed: ODPM_GOLDEN_PATH_SKIP_REFRESH=1 …/run_golden_path_test.sh
```

По умолчанию пропускаются в `unittest discover` (быстрый CI unit). `run_golden_path_test.sh` перед HTTP-тестом вызывает refresh (`odpm --skip-start`) и preflight — как job в `ci-docker.yml`.

`tests.integration.test_ci_image_build` проверяет бэкенд **`docker`**. Бэкенд **`kaniko`** (argv, `docker-run` / `direct`, fail-fast без docker config) покрыт unit-тестами `tests.test_ci_image_build_backends` — см. [ADR-016](adr-016-ci-image-build-backends.md).

Флаги и таймауты jobs: [ADR-006](adr-006-integration-gate-policy.md), [ci.md](ci.md).

## Host / architecture notes

Эталон merge-gate для unit — **Linux** (`ubuntu-latest`). Локальные отличия:

| Среда | Что ожидать | Как относиться |
|-------|-------------|----------------|
| **Linux + `gpg` в PATH** | Ближе всего к CI | Регрессии unit здесь — сигнал чинить код/тест |
| **macOS** (`/var/folders` ↔ `/private/var/folders`) | Ложные `data_path` drift (`test_database_resolve`, `test_plan_database_drift`, связанные ci db override); `test_vscode_python_paths` может сравнивать абсолютные `/private/...` с относительными `sources/...` | Не блокеры merge, если CI **unit** зелёный ([ADR-023](adr-023-local-unit-parity.md)) |
| **macOS без `gpg`** | ERROR в `test_apt_repo_scripts` / `test_yum_repo_scripts` (`FileNotFoundError: gpg`) | Установить GnuPG (`brew install gnupg`) или игнорировать локально |
| **Apple Silicon + Docker** | Desktop должен быть запущен; linux/amd64-образы могут идти через эмуляцию | Только для opt-in integration / smoke |
| **IDE sandbox** | Падения docker sock, git init, запись `.vscode`, отсутствие `gpg` | Перезапуск без sandbox; не считать багом odpm |

Новые стабильные host-флейки добавляйте в эту таблицу; смену политики — в [ADR-023](adr-023-local-unit-parity.md).
