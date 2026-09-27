# user_settings.json file fields

> **AI-translated** from Russian.

The file describes **how to work** with an already defined stack (`odpm.json`): which project to develop, which modules to install, how to create a database. If the file is missing, odpm creates it from a template.

| Field | Purpose |
|-------|---------|
| `developing_project` | Link to the developing repository or directory ([link formats](git-links.md)); supports `${VAR}` — see below |
| `init_modules` | Modules to install with bare `-i` (comma-separated, no spaces); explicit `-i sale,crm` overrides for this run |
| `update_modules` | Modules to update with bare `-u`; explicit `-u my_module` overrides for this run |
| `db_creation_data` | Parameters for a **new** database on first `-d` |
| `db_creation_data.db_lang` | *(deprecated)* Database language — prefer `database.language` in [odpm.json](odpm-json.md) |
| `db_creation_data.db_country_code` | *(deprecated)* Country code — prefer `database.country` in [odpm.json](odpm-json.md) |
| `db_creation_data.create_demo` | Whether to create demo data (default `false` in new `user_settings.json`) |
| `db_creation_data.db_default_admin_login` | Administrator login |
| `db_creation_data.db_default_admin_password` | Administrator password |
| `update_git_repos` | Whether to update git on restart |
| `clean_git_repos` | Whether to reset local changes in platform and dependencies |
| `check_system` | Docker and git checks for beginners (default `true`) |
| `dev_mode` | Odoo development mode; `developer` scenario only |
| `db_manager_password` | Odoo database manager password (on `hardened` usually `${@secret:odpm.db_manager_password}`; see [security](../operations/security.md)) |
| `sql_queries` | SQL list for `--sql-execute` |
| `pre_commit_map_files` | Files for pre-commit when not on Linux |
| `use_oca_dependencies` | Extended OCA and nested `odpm.json` resolution (default `false`) |
| `create_module_links` | Symbolic links for the editor (default `false`) |
| `sidecars` | Local compose-sidecar toggles: name → `true`/`false`. `false` drops the service from plan, fragments, and `docker-compose.yml`; missing key or `true` keeps it. Cannot list `db`/`odoo`. After change — `odpm --skip-start`. See below |

## `${VAR}` substitution in `developing_project`

Field **`developing_project`** is the only one in `user_settings.json` where odpm expands `${NAME}` / `${NAME:-default}` when reading the file. Value source: `export` / CI → project `.env` → default in the string.

```json
{
  "developing_project": "file://${DEVELOPING_PROJECT_DIR}"
}
```

```ini
DEVELOPING_PROJECT_DIR=/home/dev/my_addons
```

Other `user_settings.json` fields do **not** get substitution.

## Odoo development mode (`dev_mode`)

String of Odoo flags: `reload`, `qweb`, `werkzeug`, `xml`, `access`, `all` (see Odoo documentation). Ignored in `server` and `ci` scenarios. After a change — `odpm --skip-start`.

## System check (`check_system`)

When `true`, basic git and Docker checks run. Does not disable compose validation. Freeing occupied ports in developer mode is separate logic.

## Symbolic links (`create_module_links`)

Simplify navigation and debugging in VS Code — [dedicated article](../operations/vscode-debug.md).

## Local sidecars (`sidecars`)

Map of **logical** compose service names from the manifest/plugins (not `service_sources`, not `db`/`odoo`):

```json
{
  "sidecars": {
    "mailpit": false,
    "redis": true
  }
}
```

- `false` — service is omitted from `odpm plan` fragment steps, `.odpm/compose/fragments/`, and `docker-compose.yml`.
- missing key or `true` — service stays.
- JSON booleans only; strings like `"false"` are an error.
- Personal `false` values in a committed `user_settings.json` can surprise the team/CI — coordinate or keep the override local.
- After a change: `odpm --skip-start` (same as after changing `dev_mode`). Details: [ADR-025](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-025-local-sidecar-gates.md).
