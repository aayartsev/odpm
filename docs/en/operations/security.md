# Security

## Security profiles

The **`ODPM_SECURITY_PROFILE`** / **`--security-profile`** axis sets posture (passwords and publish binds), separate from `ODPM_SCENARIO` (topology / workflow).

| Profile | Scenario default | New `user_settings` / secrets | Published ports |
|---------|------------------|-------------------------------|-----------------|
| `convenience` | `developer` | manager=`1`, admin user=`admin` (unchanged) | no forced `127.0.0.1` |
| `hardened` | `server` | random in `.odpm/secrets.json`; settings use `${@secret:odpm.db_manager_password}` and `${@secret:odpm.db_default_admin_password}` | Postgres and all published → `127.0.0.1` |

Override: CLI `--security-profile` wins over env `ODPM_SECURITY_PROFILE`, else scenario default.  
**`ci`**: Odoo password secret bootstrap is **off**; port binds stay scenario-owned (postgres on localhost, not all published), even if override is `hardened`.

Source of truth for Odoo passwords is **`user_settings.json` after expand** (`${VAR}` / `${@secret:}` across the whole file). odpm **never rewrites** an existing settings file. On `hardened`, if password fields in raw settings are plaintext / empty / not `${@secret:…}` — WARNING (file unchanged).

New hardened projects: if `.odpm/secrets.json` is missing, odpm creates `odpm.db_manager_password` and `odpm.db_default_admin_password` (`token_urlsafe`, `0600`).  
An existing Odoo database does not pick up a new admin password automatically — use `--set-admin-pass` with `-d`.

See ADR-023, [local secrets](secrets.md), [user-settings](../reference/user-settings.md).

## Passwords in configuration

| Setting | Purpose |
|---------|---------|
| `db_manager_password` in `user_settings.json` | Odoo **database manager** password (`admin_passwd`) |
| `db_default_admin_login` / `db_default_admin_password` | **Administrator** account when creating a DB / `--set-admin-pass` |
| PostgreSQL credentials | Injected into service config and compose (shared `POSTGRES_ODOO_PASS` for now) |

On a **laptop** (`convenience`), template defaults are fine. On a **server** (`hardened`), prefer secrets + refs.

## Secrets and git

Do not commit passwords, API tokens, or private keys. Project `.env` is usually **not** committed. Prefer `user_settings.json` without real secrets in git (on hardened — `${@secret:…}` refs).

### Module secrets (API keys, integration tokens)

Use **`.odpm/secrets.json`** (gitignored). odpm mounts a normalized copy at `/run/odpm/secrets.json` (`developer` and `server`).

- Commit only **`.odpm/secrets.example.json`** with `REPLACE_ME` stubs.
- After import, odpm sets source mode **`0600`**.
- Do not log `/run/odpm/secrets.json` values or duplicate them into compose `environment:`.

Details: [local secrets](secrets.md).

`--secrets-file` imports JSON v1 into `.odpm/secrets.json` **early in bootstrap** (before full `user_settings` `${@secret:}` expand).

## `server` scenario and internet exposure

Default profile **`hardened`**: localhost-only ports, passwords via secrets.

- Terminate **HTTPS** at a **reverse proxy**.
- Enable **`proxy_mode`** in `odoo.conf`; use **`dbfilter`** when hosting multiple DBs.
- Do not widen published ports to `0.0.0.0` in compose by hand.
- App role `odoo` is **NOSUPERUSER**; admin role `postgres` is still required for ensure-role. Admin and app still share `POSTGRES_ODOO_PASS` today.
- Firewall: expose SSH and the HTTPS proxy only.
- Do not use **`dev_mode`** on an internet-facing instance; it is ignored in `server`.
- Debugger port is not needed on the server.

## Local development

Default profile **`convenience`**: simple passwords and open ports for local tools. To try a production-like layout: `ODPM_SECURITY_PROFILE=hardened` or `--security-profile hardened` without changing scenario.
