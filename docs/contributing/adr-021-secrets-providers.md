# ADR-021: Secrets providers (file + Infisical)

## Status

Accepted (4.7+).

## Context

Module secrets already flow `.odpm/secrets.json` → `secrets.materialize` → `/run/odpm/secrets.json` and `${@secret:}`. Teams also keep secrets in Infisical (or a future vault). odpm must fetch them **once per process** into the same source file so expand, materialize, and CI bake share one snapshot — without new pip dependencies and without changing the module contract.

## Decision

1. **`SecretsProvider` protocol** — `fetch(...)` returns a flat `dict[str, str]` (schema v1). Orchestration (`ensure_secrets_source`) writes `.odpm/secrets.json`. Providers do not see `SecretsFetchSession`.
2. **Built-ins** — `file` (current `--secrets-file` / existing source) and `infisical` (Universal Auth via stdlib `urllib`). Third-party: entry point group `odpm.secrets_providers`.
3. **Type precedence** — `--secrets-provider` > `ODPM_SECRETS_PROVIDER` > `secrets.provider.type` > `file`. `--secrets-file` **forces** `file` for that run.
4. **Credentials** — only process env / layered `.env` (`INFISICAL_CLIENT_ID`, `INFISICAL_CLIENT_SECRET`, optional `INFISICAL_HOST`, `INFISICAL_ENVIRONMENT_SLUG`). Wizard does not prompt for these keys.
5. **One snapshot per process** — `OdpmPipeline.setup` creates `SecretsFetchSession` and hangs it on `Config` before bootstrap. `ensure_secrets_source` is the only API/import entry. Yesterday’s `.odpm/secrets.json` does **not** skip fetch. Prepare does not duplicate an early fetch.
6. **Early hook** — after `json.load` of raw `odpm.json` in `OdpmJsonReader.get_odpm_settings`, **before** `${@secret:}` expand. `odpm.json` may appear only after developing-repo clone; dotenv already exists (`CreateUserEnvironment` before `Config`).
   | Condition | Early |
   |-----------|--------|
   | `file` + `--secrets-file` | import |
   | `file` without flag | nothing |
   | remote **and** `${@secret:}` in the effective slice | fetch now |
   | remote **without** `${@secret:}` | defer to prepare (no network on setup) |
7. **Prepare** — step `secrets.fetch` **before** `secrets.materialize`. In `ci` fetch is **not** skip (materialize still skip). Plan text: provider name and key count, never values.
8. **CI bake** — `prepare_secrets_for_ci_bake(project_dir, config)` always calls `ensure_secrets_source` on the **same** `config.session`, then materialize. No `os.path.isfile(source)` short-circuit.
9. **Infisical HTTP** — `POST /api/v1/auth/universal-auth/login` then `GET /api/v4/secrets`; timeout 30s; errors include status and path, **never** the response body. No token cache: one fetch = two HTTP calls.
10. **Overlay** — `scenarios.*.secrets.provider` **replaces** the whole provider object (`keys` / `required` keep the previous merge). Runtime `effective_infisical_config()` enforces exactly one of `project_id` / `project_slug` and a required `environment_slug` (not JSON Schema `oneOf`).

### `--plan` side effect

`--plan` + remote provider + `${@secret:}` in the effective slice **does** call the API and writes `.odpm/secrets.json` during setup — otherwise expand cannot run. `--plan` without `${@secret:}` does **not** hit the network on setup (fetch waits for prepare; `--plan` still evaluates `secrets.fetch` as `update` but does not execute it).

## Consequences

- Consumers (modules, `${@secret:}`, bake) are unchanged.
- No `infisicalsdk` / `requests` / `httpx` in `pyproject.toml`.
- File provider does **not** enforce `secrets.required` (that stays in `ensure_secrets_requirements_met`).
- Tests mock HTTP (inject transport / patch `urlopen`); no live Infisical in CI.

## References

- [docs/operations/secrets.md](../operations/secrets.md)
- [docs/reference/odpm-json.md](../reference/odpm-json.md)
- [ADR-002](adr-002-ci-secrets-bake.md)
