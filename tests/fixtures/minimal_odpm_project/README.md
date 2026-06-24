# Minimal odpm project fixture (compose-smoke)

In-repo stub project for **CI `compose-smoke`** and local `./scripts/run_compose_smoke_test.sh`.

- **Not** a full Odoo tree — platform and developing directories are created by [`minimal_odpm_fixture.py`](../minimal_odpm_fixture.py) with stub `odoo-bin` / git metadata.
- **CI gate (v1 flat):** every push/PR runs `ComposeSmokeIntegrationTests` (`python -m dev_project.cli --skip-start --no-git-update`, then `docker compose config`).
- **CI gate (v2 Mailpit):** `ComposeSmokeMailpitIntegrationTests` when `ODPM_COMPOSE_SMOKE_MAILPIT=1` — nested manifest with `services.mailpit` (reference spec from `dev_project.extensions.reference.mailpit`).
- **HTTP smoke (T2, mandatory on `4.6.0-dev` PR):** `HttpSmokeIntegrationTests` when `ODPM_RUN_HTTP_SMOKE=1` — Mailpit `compose up` + HTTP 200 (`./scripts/run_http_smoke_test.sh`). See [ADR-006](../../docs/contributing/adr-006-integration-gate-policy.md).
- **Full E2E** (`golden-path`, Odoo HTTP 200 `/web`) runs on a self-hosted runner when `ODPM_GOLDEN_PATH_ENABLED=true` and secret `ODPM_GOLDEN_PATH_PROJECT` is set — see [contributing/ci.md](../../../docs/contributing/ci.md).
