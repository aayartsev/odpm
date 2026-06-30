# user_settings.json file fields

> **AI-translated** from Russian.

The file describes **how to work** with an already defined stack (`odpm.json`): which project to develop, which modules to install, how to create a database. If the file is missing, odpm creates it from a template.

| Field | Purpose |
|-------|---------|
| `developing_project` | Link to the developing repository or directory ([link formats](git-links.md)); supports `${VAR}` — see below |
| `init_modules` | Modules to install with `-i` (comma-separated, no spaces) |
| `update_modules` | Modules to update with `-u` |
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
| `db_manager_password` | Odoo database manager password |
| `sql_queries` | SQL list for `--sql-execute` |
| `pre_commit_map_files` | Files for pre-commit when not on Linux |
| `use_oca_dependencies` | Extended OCA and nested `odpm.json` resolution (default `false`) |
| `create_module_links` | Symbolic links for the editor (default `false`) |

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
