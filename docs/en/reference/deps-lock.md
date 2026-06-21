# deps.lock.json version lock file

> **AI-translated** from Russian.

Path: **`.odpm/deps.lock.json`**. Pins **git revisions** (and fingerprints for `file://`) for platform, dependencies, and optionally the developing project. The file is **committed to git**, like lock files in the Node or Python ecosystem.

## Commands

| Action | Command |
|--------|---------|
| Recompute lock | `odpm --update-lock --skip-start` |
| Prepare using existing lock | `odpm --skip-start` |
| Regenerate Docker files only, no git | `odpm --no-git-update --skip-start` (lock **not** used) |

After changing `dependencies`, `oca_dependencies.txt`, or nested `odpm.json` in dependencies — update the lock and commit.

## Rule priority

`--no-git-update` → `--update-lock` → read lock → branch tip / nightly date.

## Two lock sources (v1 flat vs v2 nested)

| `odpm.json` format | Canonical SHA source | Role of `.odpm/deps.lock.json` |
|--------------------|----------------------|--------------------------------|
| **v1 flat** (no `manifest_schema: 2`) | `.odpm/deps.lock.json` | Sole source; commit to git |
| **v2 nested** with non-empty `locks.git` | **`locks.git` in `odpm.json`** | Operational copy for tooling and legacy paths |

On **v2**, `DepsLockManager` reads pins from `locks.git`. File `.odpm/deps.lock.json` remains on disk after migration and on `--update-lock`.

**Where to edit SHAs:**

- v1 — edit `.odpm/deps.lock.json` or recompute `odpm --update-lock --skip-start`.
- v2 — edit `locks.git` in `odpm.json` (canonical); then `odpm --update-lock --skip-start` to sync `.odpm/deps.lock.json`.

**Source mismatch:** if `locks.git` and `.odpm/deps.lock.json` differ, `odpm plan` shows a warning and step `git.lock_verify` logs a warning. Canonical is `locks.git`; use `--update-lock` to align the on-disk file.

See [manifest-migration.md](manifest-migration.md#locks-after-migration-v2).

## Contents (schema version 1)

- `platform` — Odoo platform or fork repository;
- `developing` — developing project repository;
- `dependencies` — full resolved graph (including transitive OCA).

Each entry has: `url`, `commit`, optionally `branch`, `kind` (`git` or `file`).

The lock stores **expanded** URLs and paths (after `${VAR}` substitution in manifest). Reading an existing lock file does **not** perform substitution.

## Local directory `file://`

For platform via `file://`, field `commit` stores a **content fingerprint** of the directory, not a git hash. A remote repository is more reliable for team work and builds.

## Developer mode

The lock applies to **platform and dependencies**, but does **not force** git state of the **developing** project — branch and commits stay under the developer’s control. Field `developing` in the lock is still written on `--update-lock` and **strictly checked** in `ci` and `server` scenarios.

See [coordinator role](../scenarios/team-coordinator.md).
