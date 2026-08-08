# Тесты

## Unit

```bash
cd /path/to/odpm
pip install -e ".[test]"
python3 -m unittest discover -s tests -p 'test_*.py'
```

CI: push/PR в `4.0-beta`, `4.0-rc1`, `main` — Python 3.10 и 3.12.

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

Правила: `pyproject.toml` `[tool.ruff]`.

## Docker integration (opt-in)

```bash
./scripts/run_compose_smoke_test.sh
ODPM_RUN_DOCKER_INTEGRATION=1 python3 -m unittest tests.integration.test_ci_image_build -v
ODPM_GOLDEN_PATH_PROJECT=/path ./scripts/run_golden_path_test.sh
```

По умолчанию пропускаются в `unittest discover` (быстрый CI).

`tests.integration.test_ci_image_build` проверяет бэкенд **`docker`**. Бэкенд **`kaniko`** (argv, `docker-run` / `direct`, fail-fast без docker config) покрыт unit-тестами `tests.test_ci_image_build_backends` — см. [ADR-016](adr-016-ci-image-build-backends.md).
