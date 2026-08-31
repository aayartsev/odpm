# ADR-022: Scenario-aware odoo_conf frozen keys

## Status

Accepted (4.7+).

## Context

odpm reserves certain `odoo_conf.options` keys so the manager can own addons paths, data dir, admin password, HTTP port, and compose-linked database credentials. Teams running CI against an **external** PostgreSQL need to set `db_host` / `db_port` / `db_user` / `db_password` in the effective `ci` slice (often via `${@secret:}`). A single global reserved set blocked that without inventing a parallel manifest block or an `external` flag.

## Decision

1. **Two frozen layers** — **global** (`addons_path`, `data_dir`, `admin_passwd`, `http_port`) forbidden in every scenario; **scenario** (`db_host`, `db_port`, `db_user`, `db_password`) forbidden in `developer` / `server`, **allowed** in effective `ci`.
2. **No new manifest block** — overrides use ordinary `scenarios.ci.odoo_conf.options` (and optional root merge into the `ci` effective slice).
3. **No `external` flag** — runtime derives “CI uses external DB credentials from manifest” from presence of any `db_*` key in effective `ci` options (`manifest_ci_db_override` / `ci_manifest_db_override`).
4. **Validate post-schema** — JSON Schema unchanged; `validate_manifest_odoo_conf(fragment, scenario=…)` and `validate_scenario_manifest` check overlays and each effective slice with scenario-aware frozen sets. Error lists the **full** frozen key set for that scenario.
5. **Compose postgres** — odpm does **not** remove the compose `db` service automatically when `db_*` are set.
6. **Credentials** — prefer `${@secret:…}` / `${VAR}`; literal `db_password` in git is discouraged (optional warning later; v1 does not block).
7. **Runtime follow-ups (same ADR)** — when CI manifest DB override is active, skip false-positive `template.odoo_conf` regen / `db_host_mismatch` drift against the compose service name. Merge already applies manifest `db_*` into `odoo_config_data`; container wait already reads host/port from config.

## Consequences

- aktta-style CI overlays with external DB pass `odpm manifest validate` / `load_manifest`.
- Putting `db_*` in `developer` or `server` remains a hard `ConfigError`.
- Host `ensure_app_role` / `odpm database` still target compose postgres; external DB role bootstrap stays out of scope for odpm.
- Deprecated alias `ODOO_CONF_RESERVED_OPTION_KEYS` remains as the union of both layers for docs migration.

## References

- [docs/reference/odoo-conf.md](../reference/odoo-conf.md)
- [docs/scenarios/ci.md](../scenarios/ci.md)
- [ADR-011](adr-011-scenario-manifest-overrides.md)
- [ADR-021](adr-021-secrets-providers.md)
