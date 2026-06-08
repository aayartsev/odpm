# Minimal odpm project fixture (compose-smoke)

In-repo stub project for **CI `compose-smoke`** and local `./scripts/run_compose_smoke_test.sh`.

- **Not** a full Odoo tree — platform and developing directories are created by [`minimal_odpm_fixture.py`](../minimal_odpm_fixture.py) with stub `odoo-bin` / git metadata.
- **CI gate:** every push/PR runs `tests.integration.test_compose_smoke` (`odpm --skip-start --no-git-update`, then `docker compose config`).
- **Full E2E** (`golden-path`, HTTP 200) requires a real initialized project via secret `ODPM_GOLDEN_PATH_PROJECT` — see [README.MD](../../../README.MD#docker-ci) CI matrix.
