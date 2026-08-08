# Server scenario (`server`)

> **AI-translated** from Russian.

The **`ODPM_SCENARIO=server`** variable runs Odoo as a **service** on a virtual machine, VPS, or test stand: without a debugger in the Odoo process, with restricted PostgreSQL access.

## Purpose

Suitable when you need the **same project composition** as the developer (same repositories and versions from `odpm.json`), but the environment is **not intended for debugging** from a laptop. Typical cases: customer demo on a single virtual machine, internal test stand, "light" production setup without a heavy image build pipeline.

A full pipeline with an image registry is **not required** — `docker compose up` and a reverse proxy are enough.

## Environment behavior

| Area | How it works |
|------|--------------|
| **Debugger** | Not installed and debug port is not published. For debugging, use a separate machine with the `developer` scenario. |
| **PostgreSQL on host** | Listens only on `127.0.0.1` — cannot connect from other machines through this port mapping. |
| **Odoo and Gevent** | Ports are more broadly available on the host; for internet access use a **reverse proxy** (nginx and similar) and a firewall. |
| **Odoo development mode** | The `dev_mode` field in `user_settings.json` is **ignored** (warning in the log). |
| **Python warnings in logs** | The `PYTHONWARNINGS` variable is **not** set: on Odoo startup the log may show `DeprecationWarning` from **docutils** (often with traceback). This is noise from a dependency in the virtual environment, not a sign of broken project modules; if needed, update docutils in requirements or pin a compatible version. In the `developer` scenario odpm intentionally hides such messages. |
| **Sources** | Same as developer — mounted from the server disk. |
| **Module secrets** | Same as `developer`: `.odpm/secrets.json` is mounted at `/run/odpm/secrets.json` (read-only). Deliver the file to the server via `odpm --secrets-file` or copy; see [local secrets](../operations/secrets.md). |
| **Docker Compose** | `db` and `odoo` services use `restart: unless-stopped` — containers come back after a host reboot (with `docker compose up -d`). |

## Security recommendations

- Set **strong passwords** — see [security](../operations/security.md).
- Terminate **HTTPS** at nginx; in `odoo.conf` set `proxy_mode` and `dbfilter` if needed.
- Do not expose Odoo and PostgreSQL ports to the internet unless necessary.
- To pin the platform version use `odoo_build_date` / `--odoo-build-date` (git checkout by date), not a separate archive download.

## Typical administrator commands

```bash
odpm --skip-start
docker compose up -d
odpm -d prod_db --db-backup
odpm -d prod_db -u
```
