# Odoo configuration file (odoo.conf)

> **AI-translated** from Russian.

## Location

In the **root of the odpm project directory**, file **`{platform_name}.conf`**. For the standard platform this is usually **`odoo.conf`**. The name depends on `platform_name` in `odpm.json`.

## Why a file on disk when Odoo runs in a container

A developer or administrator **edits configuration the usual way** — a text file in the project directory. odpm does **not** require entering the container to change, for example, `proxy_mode` or log level.

On every environment prepare, odpm:

1. **Reads** your file from disk.
2. **Applies** overrides from `odoo_conf` in `odpm.json` (if set) — manifest **overrides** disk.
3. **Substitutes** database connection parameters from the service configuration.
4. **Recalculates** addon paths (`addons_path`) and data directory (`data_dir`) as the process sees them **inside the container** (they differ from host paths).
5. Writes the result to the service JSON (`.odpm/runtime/config.json`).
6. On container start, the entrypoint **creates** the configuration file **inside** the container and passes Odoo `-c` with that path.

So the file in the project directory is **your configuration interface**; the container receives a **consistent** version with correct paths.

## What you may edit manually

Parameters from Odoo documentation: `proxy_mode`, `dbfilter`, `log_level`, worker count, etc. Extra **INI sections** for modules (`[redis_server]`, `[s3_server]`, …) may be declared in manifest `odoo_conf` next to `options` — see [odpm.json fields](odpm-json.md#odoo_conf-block-odoo-option-overrides).

On a server reachable from the internet, **`proxy_mode`** and **`dbfilter`** are usually set together with a reverse proxy (nginx). For CI/preview you can set the same keys in **`odoo_conf`** in `odpm.json`.

## Source priority

```text
odpm-managed (addons_path, data_dir)  ← always wins
    ↑
manifest odoo_conf.options            ← overrides disk
    ↑
odoo.conf on disk                     ← local defaults
```

## What odpm overwrites on prepare

- **`addons_path`** — full list of addon paths inside the container;
- **`data_dir`** — Odoo data directory inside the container;
- **`db_host`** — by default synced with the **physical** postgres service name from `.env` (`POSTGRES_SERVICE_NAME` or `{prefix}db` when `ODPM_COMPOSE_PREFIX` is set);
- database placeholders in the template — real values from runtime;
- **`admin_passwd`** — in the container from `db_manager_password` (not from manifest).

### Two-layer frozen policy (ADR-022)

Manifest `odoo_conf.options` uses a scenario-aware policy:

| Layer | Keys | Forbidden in |
|-------|------|----------------|
| **Global** | `addons_path`, `data_dir`, `admin_passwd`, `http_port` | every scenario |
| **Scenario** | `db_host`, `db_port`, `db_user`, `db_password` | `developer` and `server`; **allowed** in the effective `ci` slice |

`odpm manifest validate` / `load_manifest` list the **full** frozen key set for the current scenario on violation. There is no separate override block and no `external` flag: any `db_*` in effective `ci` options is the derived runtime signal.

When `scenarios.ci.odoo_conf.options` sets `db_*` (external DB), step **`template.odoo_conf`** does not regen for compose `db_host_mismatch`, and plan omits false **`db_host_mismatch`** drift. odpm does **not** remove the compose `db` service automatically. Host `ensure_app_role` / `odpm database` still target compose postgres. See [ADR-022](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-022-odoo-conf-scenario-frozen.md).

If on-disk `db_host` does not match the expected postgres service name **and** CI override is inactive, step **`template.odoo_conf`** recreates the config; `odpm plan` shows drift **`db_host_mismatch`**. See [PostgreSQL state](database-state.md).

## When the file is recreated entirely

If the file is missing, corrupted, or required database parameters are empty — odpm creates a template again.

After changes affecting paths or addon composition: `odpm --skip-start` and restart containers.

## Image build scenario (`ci`)

The same configuration logic is **baked into the image** on `odpm --build-image`.
