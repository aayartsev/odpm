# Security

> **AI-translated** from Russian.

## Passwords in configuration

| Parameter | Purpose |
|-----------|---------|
| `db_manager_password` in `user_settings.json` | Odoo **database manager** password |
| `db_default_admin_login` / `db_default_admin_password` | **Administrator** account when creating a new database |
| PostgreSQL credentials | Injected into service configuration and compose |

On **your own computer** in development mode, default template values are acceptable — the database is not reachable from the internet.

On a **server**, customer VM, or test stand on the organization network, set passwords **explicitly**: long and unique. Do not rely on “factory” values from the example.

## Secrets and git

Do not put passwords, access tokens, or private keys in a shared repository. The project `.env` is usually **not committed**. Keep the `user_settings.json` template in git without real secrets.

### Odoo module secrets (API keys, integration tokens)

For arbitrary **module** keys (not Odoo DB passwords), use **`.odpm/secrets.json`** — a file in `.odpm/.gitignore`, not in `odpm.json`. odpm mounts a normalized copy into the container as `/run/odpm/secrets.json` (`developer` and `server` scenarios).

- Commit only **`.odpm/secrets.example.json`** to git with `REPLACE_ME` placeholders.
- After import, odpm sets **`0600`** permissions on the source.
- Do not log values from `/run/odpm/secrets.json` in Odoo and do not duplicate them in compose `environment:`.

Details: [local secrets](secrets.md).

## `server` scenario and internet exposure

- Terminate **HTTPS** at a **reverse proxy** (nginx, Caddy, traefik, etc.).
- Enable **`proxy_mode`** in `odoo.conf`; when publishing multiple databases on one host, configure **`dbfilter`**.
- PostgreSQL in this scenario listens only on **127.0.0.1** on the machine — odpm configures port forwarding that way. Do not manually expose `5432` on all interfaces in compose.
- **Firewall:** open SSH and HTTPS proxy from outside; Odoo ports (`8069`, `8072`) do not need to be visible from the internet if the proxy is on the same machine.
- Do not use Odoo **development mode** (`dev_mode`) on an externally reachable instance; in `server` scenario it is ignored, but switching to `developer` on production for debugging is **not allowed**.
- A debugger port on the server is **not needed**.

## Development on localhost

Default passwords are convenient for a quick start. Do not carry them to staging environments and do not expose a dev environment on a shared network without changing passwords and adding a proxy.
