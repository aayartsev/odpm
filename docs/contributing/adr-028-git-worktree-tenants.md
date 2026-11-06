# ADR-028: Per-tenant git worktrees under `ODOO_PROJECTS_DIR`

## Status

Accepted (4.8-dev track).

## Context

Parallel CI jobs (for example one directory per merge request) often share the same Odoo pin and dependency URLs. A classic full clone per job wastes disk and still risks fighting over a single working tree if jobs share one checkout. Akta and similar platforms want a shared object store with an isolated working tree per tenant directory, without changing the project-facing symlink contract.

Sharing one platform worktree by commit SHA across tenants is a later optimization; this ADR ships the safer first step: **one worktree per tenant + repository**.

## Decision

1. **Opt-in only.** Default remains classic `git clone` into `ODOO_PROJECTS_DIR`. Enable with `ODPM_GIT_WORKTREE=1` (truthy: `1` / `true` / `True` / `yes` / `YES`) or CLI `--git-worktree` on the same commands that already expose `--no-git-update`. Either is enough.

2. **Tenant id** = `basename(project_dir)` (example: `mr-42`). Unsafe path characters are rejected with `ConfigError`. No separate env override in this version.

3. **Layout under `ODOO_PROJECTS_DIR`:**
   - bare mirrors: `mirrors/<repo-key>.git` (fetch / deepen);
   - worktrees: `worktrees/<tenant>/<repo-key>/` at the resolved commit (detached HEAD);
   - repo-key is the stable relative path from the existing git link parser (for example `github.com/odoo/odoo`).

4. **`service_sources`:** in worktree mode, remote sources use the same `mirrors/` + `worktrees/<tenant>/…` layout (not `service-sources/<name>`). Project symlinks still point at the worktree path. Classic `service-sources/<name>` remains when the mode is off.

5. **No migration of old clones.** Worktree mode only writes under `mirrors/` and `worktrees/`. Existing working copies beside them are left alone.

6. **Materialize:** under a file lock per mirror — fetch bare → `git worktree add` (reuse if the path is already on the same SHA) → project symlinks to the worktree. If the path exists on another SHA and `--no-git-update` is **not** set — `worktree remove` + add. Do not `git checkout` inside a shared working tree.

7. **`odoo_build_date` / deepen:** resolve and deepen history in the **bare** mirror, then point the tenant worktree at the found SHA.

8. **`file://` and local trees:** always classic behaviour even when the flag is on.

9. **`--no-git-update`:** no fetch; reuse when the worktree exists on the expected SHA; otherwise `ConfigError` (no remove/recreate).

10. **One filesystem:** bare and worktrees must share a filesystem (cluster: one volume). Cleanup of tenant worktrees is manual in this version (`git worktree remove` / delete under `worktrees/<tenant>/`); no odpm prune command yet.

11. **Out of scope here:** share-by-SHA across tenants; thin plan/ensure without an Odoo tree; meta-image/PVC packaging; auto-migration of full clones; tenant id override env.

## Consequences

- CI can run parallel tenants against one object store with isolated checkouts.
- Disk use is higher than share-by-SHA until that follow-up lands.
- Docs: `project-layout.md`, `cli.md`, `env-dotenv.md`, `scenarios/ci.md`.

## References

- Plan: `.cursor/plans/git_worktree_тенант_951ebac4.plan.md`
- Related: ADR-015 (service_sources), ADR-027 (layered CI images)
