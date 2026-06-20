# odpm.json and user_settings.json

> **AI-translated** from Russian.

odpm intentionally **splits** settings into two levels: what belongs to the **reproducible stack for the whole team**, and what belongs to **day-to-day work of a specific developer**.

## odpm.json — stack description

Stored in git with the modules (as a rule). Defines **what the project is built from**:

- Odoo, Python, Linux distribution, PostgreSQL versions;
- **platform** repository URL and fork package name;
- list of **git dependencies** and Python packages;
- language and country for a **new database** (`database`) for the whole team.

**Who edits:** lead developer, coordinator, infrastructure owner — after team discussion.

## user_settings.json — working settings

Describes **how to work with this stack right now**:

- link to the **developing** repository or directory;
- which modules to **install** (`init_modules`) and **update** (`update_modules`) on startup with `-i` / `-u`;
- **new database** parameters — language and country in **`odpm.json`** (`database`); demo data and admin credentials in `user_settings.json`;
- whether to update git repositories on every run;
- Odoo development mode (`dev_mode`) — only in the `developer` scenario;
- database manager passwords and other operational parameters.

**Who edits:** the developer on their machine; the repository may contain a template without secrets.

The file is **created automatically** from defaults if missing.

## Rule of thumb

| Question | File |
|----------|------|
| “Which versions and repositories does the project depend on?” | `odpm.json` + `.odpm/deps.lock.json` |
| “Which language and country for a new project database?” | `odpm.json` → `database` |
| “Which modules to install or update today?” | `user_settings.json` |
| “Create demo data and which admin password on this machine?” | `user_settings.json` |

Field details: [odpm.json](odpm-json.md), [user_settings.json](user-settings.md).
