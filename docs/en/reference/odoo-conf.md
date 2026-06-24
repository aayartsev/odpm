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

Parameters from Odoo documentation: `proxy_mode`, `dbfilter`, `log_level`, worker count, etc.

On a server reachable from the internet, **`proxy_mode`** and **`dbfilter`** are usually set together with a reverse proxy (nginx). For CI/preview you can set the same keys in **`odoo_conf`** in `odpm.json` — see [odpm.json fields](odpm-json.md#odoo_conf-block-odoo-option-overrides).

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
- **`db_host`** — synced with **`POSTGRES_SERVICE_NAME`** from `.env` (PostgreSQL service name in compose);
- database placeholders in the template — real values from runtime;
- **`admin_passwd`** — in the container from `db_manager_password` (not from manifest).

These and other reserved keys **cannot** appear in manifest **`odoo_conf`** — `odpm manifest validate` fails.

If `db_host` on disk does not match `POSTGRES_SERVICE_NAME`, step **`template.odoo_conf`** recreates the config; `odpm plan` shows drift **`db_host_mismatch`**. See [PostgreSQL state](database-state.md).

## When the file is recreated entirely

If the file is missing, corrupted, or required database parameters are empty — odpm creates a template again.

After changes affecting paths or addon composition: `odpm --skip-start` and restart containers.

## Image build scenario (`ci`)

The same configuration logic is **baked into the image** on `odpm --build-image`.
