# Migrating from odpm 3.0 to 4.x

> **AI-translated** from Russian.

**There is no automatic migration. Compatibility with version 3.0 is broken.**

A 3.0 environment **must not be “upgraded in place”**. You need a **new project directory** for 4.x and migration of **database data**, not configuration files in the old format.

## Recommended order

1. **Back up the database** from the 3.0 environment:
   - with `odpm --db-backup` (if the old odpm is still available), or
   - with PostgreSQL tools (`pg_dump`).
2. Create a **new** odpm environment directory (e.g. `project-17-v4/`).
3. Install **odpm 4.x** — [installation](../install/README.md).
4. Run `odpm --init` with the current repository and 4.x-format `odpm.json`.
5. Bring up the environment and **restore the database**:
   ```bash
   odpm -d database_name --db-restore archive_name
   ```
6. Update modules for the new Odoo version:
   ```bash
   odpm -d database_name -u
   ```

Keep the old 3.0 directory for reference until the team fully switches.

If you **repeat** `odpm --init` in the same environment directory (not recommended for production), the old Docker volume `*_postgres-data` may point at an outdated `data/postgres/...` path. Remove the volume before starting: `docker volume rm <project>_postgres-data` — see [non-interactive runs](non-interactive.md).

## What changed fundamentally

- Scenarios **`developer`**, **`server`**, **`ci`** instead of a single behavior.
- Lock file **`.odpm/deps.lock.json`**, command **`odpm plan`**.
- Service configuration **`.odpm/runtime/config.json`** instead of scattered parameter passing.

For developers of **odpm itself** — Python module rename table: [imports 4.0→4.1](https://github.com/aayartsev/odpm/blob/main/docs/contributing/imports-migration.md) (in the odpm repository).
