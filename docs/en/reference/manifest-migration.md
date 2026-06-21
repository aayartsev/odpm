# odpm.json v1 → v2 migration

> **AI-translated** from Russian.

Manager **odpm 4.4** reads both formats without mandatory migration. Nested **manifest v2** is opt-in: extensions (`services`, `hooks`, `locks` in the manifest), explicit `requires_odpm`.

## When to migrate

| Situation | Recommendation |
|-----------|----------------|
| Flat v1, team does not change manifest | **Do not migrate** — everything works as before |
| Need declarative compose services (Mailpit, etc.) | v2 + `services` block |
| Locks in git instead of only `.odpm/deps.lock.json` | v2 + `locks` |
| Lifecycle hooks in manifest | v2 + `hooks` |
| New project on 4.4 | v2 immediately or flat v1 (odpm writes v1 by default) |

## migrate command

```bash
cd /path/to/developing/project
odpm manifest migrate          # unified diff to stdout
odpm manifest migrate --write  # write odpm.json
```

Before `--write`, save a copy or commit the current `odpm.json`.

## What is migrated

| Source (v1 / artifacts) | v2 field |
|-------------------------|----------|
| `python_version` | `python` |
| `odoo_git_link`, `odoo_build_date` | `platform.git`, `platform.build_date` |
| `distro_name`, `distro_version` | `distro.name`, `distro.version` |
| `postgres_version` | `postgres` |
| `dependencies` | `dependencies` |
| `requirements_txt` | `requirements` |
| `developing_project` in `user_settings.json` | `developing.git` |
| `database` or `db_creation_data` | `database` |
| `.odpm/deps.lock.json` | `locks.git` (+ venv hash if present) |

## Before and after example

**v1 flat (fragment):**

```json
{
  "odpm_version": "4.0",
  "python_version": "3.12",
  "distro_name": "debian",
  "distro_version": "12",
  "postgres_version": "16",
  "odoo_version": "19.0",
  "odoo_git_link": "https://github.com/odoo/odoo.git 19.0",
  "dependencies": [],
  "requirements_txt": []
}
```

**v2 nested (equivalent + extensions):**

```json
{
  "manifest_schema": 2,
  "requires_odpm": "4.4.2",
  "platform": {
    "git": "https://github.com/odoo/odoo.git 19.0",
    "build_date": "latest"
  },
  "python": "3.12",
  "distro": { "name": "debian", "version": "12" },
  "postgres": "16",
  "dependencies": [],
  "requirements": [],
  "developing": { "git": "file:///path/to/developing" },
  "services": {
    "mailpit": {
      "image": "axllent/mailpit",
      "restart": "unless-stopped",
      "ports": ["8025:8025", "1025:1025"]
    }
  },
  "hooks": {
    "post_prepare": [["echo", "prepare done"]],
    "pre_up": []
  },
  "locks": {
    "git": {}
  }
}
```

## After migration

1. **`odpm plan`** — check prepare steps (including `compose.fragments`) and lock source warnings.
2. **`odpm up --skip-start`** — materialize without starting containers.
3. **Locks** — see [Locks after migration (v2)](#locks-after-migration-v2).
4. **Rollback** — restore v1 from git; dual-read does not require v2.

## Locks after migration (v2)

| Action | Behaviour |
|--------|-----------|
| Normal prepare | Read pins from **`locks.git`** in `odpm.json` (canonical) |
| `odpm --update-lock` | Recompute commits from disk → write **only** to `.odpm/deps.lock.json` |
| Manual SHA change | Edit **`locks.git`**; then `--update-lock` to sync deps.lock |
| Manifest ↔ deps.lock mismatch | Warning in `odpm plan` and in log on `git.lock_verify`; prepare uses manifest |

**Dual-write policy:** odpm does **not** overwrite `locks.git` on `--update-lock`. Canonical source stays in the manifest; deps.lock is an operational artifact. After dependency changes: `--update-lock`, commit the updated `.odpm/deps.lock.json`, and if needed move SHAs into `locks.git` (or rerun `odpm manifest migrate --write` from the current deps.lock).

Details: [deps-lock.md](deps-lock.md#two-lock-sources-v1-flat-vs-v2-nested).

## Compatibility

- **`odpm_version: "4.0"`** in flat v1 — format contract string, **not** the manager version.
- **`requires_odpm: "4.4.2"`** in v2 — minimum installed odpm version (semver); new projects get current `RELEASE_VERSION`.
- Details: [odpm.json](odpm-json.md), [plugins.md](plugins.md), [ADR-001](https://github.com/aayartsev/odpm/blob/4.4-dev/docs/contributing/adr-001-extensions-and-manifest-v2.md).
