# Legacy or inherited project

> **AI-translated** from Russian.

For joining an **existing** Odoo module repository — with or without `odpm.json` — rather than a greenfield tutorial setup.

## Prepare the environment directory

As with a new project, create a **separate** odpm environment directory (e.g. `client_addons-19`) and init from git:

```bash
mkdir client_addons-19 && cd client_addons-19
odpm --init git@github.com:organization/client_addons.git --branch 19.0
```

If the developing repo root already has **`odpm.json`**, odpm picks up versions and dependencies from it. If not, pass `--odoo-version` on `--init` or add `odoo_version` to the repo before connecting.

## Reading error messages

Check **odpm on the host** first — prepare, git, and config errors appear there. Service logs inside the container:

```bash
docker compose logs -f
```

Host odpm messages may be Russian when `ODPM_LOCALE=ru_RU`. Odoo and PostgreSQL logs in the container stay **English** on purpose — easier to match upstream docs.

## Editing the stack manifest

In the developing repository (or local clone after git pull), edit **`odpm.json`**:

- **`dependencies`** — git repos your modules depend on;
- **`requirements_txt`** — extra Python packages;
- for a custom core fork — **`odoo_git_link`** and **`platform_name`** ([custom platform repo](../scenarios/platform-fork.md)).

Link formats: [git, https, file](../reference/git-links.md).

## Dry-run before applying changes

Before risky edits:

```bash
odpm plan --skip-start
odpm plan --plan-show-diff --skip-start
```

Shows which prepare steps would run and how `docker-compose.yml` and runtime config would change — **without** writing disk or starting containers.

## Version lock for the whole team

After dependencies are agreed, the coordinator runs:

```bash
odpm --update-lock --skip-start
```

and commits **`.odpm/deps.lock.json`**. See [deps.lock.json](../reference/deps-lock.md) and [team coordinator](../scenarios/team-coordinator.md).

## Inherited PostgreSQL data directory

If the PostgreSQL data directory existed before odpm 4.3 (postgres log: `Skipping initialization`), on the **first** `odpm` run without `.odpm/database/last_run.json` odpm automatically:

1. starts PostgreSQL;
2. creates or updates the application role (`odoo`);
3. writes a baseline to `last_run.json`.

Diagnostics:

```bash
odpm database status
odpm plan --skip-start
```

If the role is missing and adoption has not run yet:

```bash
odpm database ensure-role
```

Changing **`POSTGRES_SERVICE_NAME`** or the port in `.env` causes **drift** vs the snapshot — odpm warns in plan. After renaming the postgres service, remove orphan containers: `docker compose down --remove-orphans`.

### Shared profile in `~/.odpm/.env` (4.7)

Since **4.7**, odpm **merges** `~/.odpm/.env` (shared paths, SSH, `ODPM_LOCALE`) with project `.env` (ports, `ODPM_COMPOSE_PREFIX`, local `${VAR}` helpers) on read; project wins on key collisions. Keep only differences in project `.env` — see [environment variables](../reference/env-dotenv.md), [ADR-013](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-013-layered-env-dotenv.md).

### Multiple odpm projects on one host (4.7)

When several odpm environments run on the **same machine** and you need isolated Docker Compose names, set a unique prefix in project `.env`:

```ini
ODPM_COMPOSE_PREFIX=acme
```

odpm rewrites `db` / `odoo` services, the `postgres-data` volume, and passes `docker compose -p acme`. In manifest and plugins keep **logical** names (`depends_on: ["db"]`). See [environment variables](../reference/env-dotenv.md), [ADR-012](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-012-compose-service-prefix.md).

### Named compose network (4.7)

To attach the full stack to an **external** reverse-proxy network (Traefik, Caddy), typically in `~/.odpm/.env`:

```ini
ODPM_COMPOSE_NETWORK=proxy
ODPM_COMPOSE_NETWORK_EXTERNAL=1
```

For a **managed** bridge network in project `.env` — `ODPM_COMPOSE_NETWORK=stack` (with prefix — physical `acme-stack`). Without these variables odpm keeps the implicit default network. See [environment variables](../reference/env-dotenv.md), [ADR-014](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-014-compose-stack-network.md).

Adoption does **not** reassign owners of existing Odoo databases in PostgreSQL. For `--db-drop` / `--db-restore` on such databases see [database state](../reference/database-state.md).

## Common issues

- **Incompatible versions** in nested dependency `odpm.json`: warning in developer, error in `ci`.
- **No SSH access** to private git: configure `~/.ssh` or `PATH_TO_SSH_KEY` in `.env` ([environment variables](../reference/env-dotenv.md)).
- **Long first platform clone** — normal; later runs are much faster.
