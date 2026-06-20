# Local secrets for Odoo modules

> **AI-translated** from Russian.

**`developer`** and **`server`** scenarios can pass arbitrary keys into the Odoo container via a **fixed path** `/run/odpm/secrets.json` (environment variable **`ODPM_SECRETS_PATH`**). In the **`ci`** scenario the host mount is **disabled** — secrets do not enter the image through this mechanism (see [CI in Actions](#ci-github-actions-developerserver-pipeline)).

## Why this exists

Integration modules often need API keys, tokens, and passwords for external services. They **should not** go in `odpm.json` or `user_settings.json` (often in git) and are **awkward** to duplicate in compose `environment:` (visible in `docker compose config`).

odpm provides a separate contract: you store values in `.odpm/secrets.json` on the host; in the container the module always reads one path.

## Project files

| File | In git | Who writes | Purpose |
|------|--------|------------|---------|
| `.odpm/secrets.example.json` | yes | odpm on init | key template without real values |
| `.odpm/secrets.json` | no | you or `--secrets-file` | **source** — the only place to edit on the host |
| `.odpm/runtime/secrets.json` | no | odpm (`secrets.materialize`) | **runtime** — mounted into the container |

On `odpm --init`, only **`secrets.example.json`** is copied. **`secrets.json`** is created manually, by copying from the example, or via CLI import.

Directory layout: [project-layout](../reference/project-layout.md). Generated artifacts: [generated-files](../reference/generated-files.md).

## Format (schema v1)

```json
{
    "schema_version": 1,
    "secrets": {
        "payment_provider.api_key": "sk_test_...",
        "custom_integration.token": "..."
    }
}
```

- `schema_version` is required, only `1`
- `secrets` — object of string → string; keys are flat (often dotted: `service.field`)
- Invalid JSON or types — error on import/materialize

## Quick start

### Option A: from template

```bash
cp .odpm/secrets.example.json .odpm/secrets.json
# edit values in .odpm/secrets.json
odpm --skip-start
docker compose up -d
```

### Option B: import on init

```bash
odpm --init file:///path/to/developing-project \
     --secrets-file /secure/vault/client-secrets.json
odpm --skip-start
```

### Option C: import on existing project

```bash
odpm --secrets-file ~/Downloads/new-secrets.json --skip-start
docker compose up -d
```

Content is copied to `.odpm/secrets.json` with permissions **`0600`**. The source file is **not deleted**.

## Full cycle after changing secrets

1. Edit **`.odpm/secrets.json`** (or call `--secrets-file` again).
2. Run **`odpm --skip-start`** — step **`secrets.materialize`** updates `.odpm/runtime/secrets.json` and rebuilds `docker-compose.yml` if needed.
3. Restart the Odoo container: **`docker compose up -d`** (or full `odpm`).
4. Verify the mount (see below).

If **`secrets.json` is deleted**, on the next materialize stale **`.odpm/runtime/secrets.json`** is removed, and the volume and `ODPM_SECRETS_PATH` disappear from compose.

## Verify the mount works

In `docker-compose.yml` for the `odoo` service (when source exists):

- variable `ODPM_SECRETS_PATH=/run/odpm/secrets.json`
- volume `.odpm/runtime/secrets.json:/run/odpm/secrets.json:ro,Z`

Inside the container:

```bash
docker compose exec odoo test -f /run/odpm/secrets.json && echo OK
docker compose exec odoo python3 -c "import json; print(list(json.load(open('/run/odpm/secrets.json'))['secrets']))"
```

Use the second command for debugging only; **do not log values** in production.

## Contract for Odoo module code

```python
import json
from pathlib import Path

SECRETS_PATH = Path("/run/odpm/secrets.json")

def load_odpm_secrets() -> dict[str, str]:
    if not SECRETS_PATH.is_file():
        return {}
    data = json.loads(SECRETS_PATH.read_text(encoding="utf-8"))
    return dict(data.get("secrets") or {})
```

The module does not care about host paths — only `/run/odpm/secrets.json`. If the file is missing, return an empty dict or handle the error per module logic.

Typical usage: write to `ir.config_parameter` on module install, or read on each request (without caching secrets in logs).

## Plan and materialize

- Prepare step **`secrets.materialize`** (before `compose.service`) copies source → runtime.
- **`odpm plan`** shows the step as `update` / `noop` / `skip` (in CI — `skip`).
- **`odpm plan --plan-show-diff`** for secrets — **summary only** (e.g. “will materialize 3 secret keys”), **without values**.

Example:

```bash
odpm plan --skip-start
odpm plan --skip-start --plan-show-diff
```

## Security

- **`.odpm/secrets.json`** is added to **`.odpm/.gitignore`** automatically on import/materialize.
- If the file exists but is not in gitignore — **`odpm plan`** emits a warning.
- Do not commit real values; keep **`secrets.example.json`** in git with `REPLACE_ME`.
- Do not put application secrets in **`odpm.json`**, **`user_settings.json`**, or the project root **`.env`** (for structured keys).
- More detail: [security](security.md).

## By scenario

| Scenario | Mount secrets | Notes |
|----------|---------------|-------|
| `developer` | yes | typical local dev |
| `server` | yes | deliver `secrets.json` to the VM (`--secrets-file` or copy) |
| `ci` | no | runtime config in the image; application secrets — separate deploy process |

### CI (GitHub Actions, developer/server pipeline)

In the **`ci`** scenario (`odpm --build-image`) host secret mount is **still disabled** — secrets do not enter the image through this mechanism.

For a **local developer/server pipeline** in Actions, use ephemeral JSON and `--secrets-file`:

```yaml
- name: Materialize module secrets for odpm project
  run: |
    cat > /tmp/odpm-ci-secrets.json <<'EOF'
    {"schema_version":1,"secrets":{"payment.api_key":"${{ secrets.MODULE_PAYMENT_API_KEY }}"}}
    EOF
    chmod 600 /tmp/odpm-ci-secrets.json
    odpm --secrets-file /tmp/odpm-ci-secrets.json --skip-start
  working-directory: /path/to/odpm-project
```

The odpm repository verifies the contract in **`tests/test_ci_secrets_smoke.py`** (job `compose-smoke` in `ci-docker.yml`). Do not print secret values in logs.

**Follow-up (Phase B, 4.4.1):** bake secrets into the CI image with `ODPM_BAKE_SECRETS=1` during `odpm --build-image` — see [ADR-002](https://github.com/aayartsev/odpm/blob/4.4-dev/docs/contributing/adr-002-ci-secrets-bake.md).

### CI image bake (`ODPM_BAKE_SECRETS=1`)

For the **`ci`** scenario, module secrets are **not mounted** from the host on `docker compose up`. For modules to see keys inside the image:

```bash
# 1. Ephemeral secrets on the runner (do not commit)
cat > /tmp/odpm-ci-secrets.json <<'EOF'
{"schema_version":1,"secrets":{"payment.api_key":"${{ secrets.MODULE_PAYMENT_API_KEY }}"}}
EOF
chmod 600 /tmp/odpm-ci-secrets.json
odpm --secrets-file /tmp/odpm-ci-secrets.json --skip-start

# 2. Bake into the image (explicit opt-in)
export ODPM_BAKE_SECRETS=1
odpm --build-image --image-tag myregistry/client-odoo:17.0
```

The image gets `COPY runtime/secrets.json → /run/odpm/secrets.json` and `ENV ODPM_SECRETS_PATH`. Without the flag or without `.odpm/secrets.json`, bake does not run.

## Difference from `.env` and Odoo passwords

| Mechanism | Purpose |
|-----------|---------|
| `.env` | ports, directories, `ODPM_SCENARIO` |
| `user_settings.json` | Odoo DB/admin passwords, modules, git |
| `.odpm/runtime/config.json` | odpm host→container service contract |
| **`.odpm/secrets.json`** | arbitrary keys for **your modules** (payment, SMTP API, …) |

## Working as a team

1. Fill **`.odpm/secrets.example.json`** with the list of required keys.
2. Each developer creates a local **`.odpm/secrets.json`** (not in git).
3. When adding keys to the project: `cp .odpm/secrets.example.json .odpm/secrets.json` and fill values, or `odpm --secrets-file …` from corporate vault.

## Troubleshooting

| Symptom | What to check |
|---------|---------------|
| No `/run/odpm/secrets.json` in container | Is `.odpm/secrets.json` present? Did you run `odpm --skip-start`? Scenario not `ci`? |
| Stale values after edit | `odpm --skip-start` + `docker compose up -d` |
| Schema error | `schema_version: 1`, all values are strings |
| Compose without volume | Remove source and regenerate compose; or add source and run `odpm --skip-start` again |

CLI flag: [`--secrets-file`](../reference/cli.md).
