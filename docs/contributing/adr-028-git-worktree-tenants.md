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

5. **No migration of old clones.** Worktree mode only writes under `mirrors/` and `worktrees/`. Existing working copies beside them are left alone (may be read as a seed source).

6. **Materialize (inside existing prepare steps):** no new prepare step ids. Per repository, under a file lock: fill bare → final SHA → one `git worktree add` (reuse if already on that SHA). Project symlinks point at the worktree. Do not `git checkout` inside a shared working tree. Flag changes *how* `git.materialize_*` / `sources.materialize` fill disk, not the registry order.

7. **Seed from classic (amendment):** if bare is missing and `{ODOO_PROJECTS_DIR}/{repo-key}/` is a git tree whose `origin` matches the link URL, create the bare with `git clone --bare` from that path and set `origin` to the link URL (no origin network for the seed itself). If bare exists but lacks a needed object, `git fetch` from the classic path. Never `clone --bare` over an existing mirror.

8. **Narrow bare fetch:** do **not** sync all heads/tags. Prefer seed; else `clone --bare --depth 1` (with `-b` when branch/`odoo_version` applies and commit is not explicit); then fetch only the target commit/branch/tip. Depth stays 1 until build-date deepen. Failed commit fetch raises `GitError` with no wide fallback.

9. **`odoo_build_date` / deepen:** for platform in worktree mode — set `worktree_mirror` on the bare **before** resolve; run `apply_build_date` (shallow-since / deepen) in the bare **before** the first worktree add. Tip after depth 1 is not the final slice. Deepen only inside the build-date resolver.

10. **`file://` and local trees:** always classic behaviour even when the flag is on.

11. **`--no-git-update`:** origin network forbidden; disk seed / fetch from matching classic allowed when objects exist locally; reuse worktree on expected SHA; otherwise `ConfigError` (including unresolved build date from local history only).

12. **One filesystem:** bare and worktrees must share a filesystem (cluster: one volume). Cleanup of tenant worktrees is manual in this version (`git worktree remove` / delete under `worktrees/<tenant>/`); no odpm prune command yet. **Self-heal on materialize:** if the checkout directory is gone but the bare still lists it (“missing but already registered”), `ensure_worktree_at_sha` runs `git worktree prune` (and retries `add --force` once) before failing — common after shared PVC / interrupted jobs.

13. **Out of scope here:** share-by-SHA across tenants; sources change check without an Odoo tree (see ADR-027); meta-image/PVC packaging; auto-migration/deletion of classic clones; tenant id override env; narrow fetch on the classic (non-worktree) path; separate prepare steps only for worktree.

## Consequences

- CI can run parallel tenants against one object store with isolated checkouts.
- Disk use is higher than share-by-SHA until that follow-up lands.
- Docs: `project-layout.md`, `cli.md`, `env-dotenv.md`, `scenarios/ci.md`.

## References

- Plan: `.cursor/plans/git_worktree_тенант_951ebac4.plan.md`
- Related: ADR-015 (service_sources), ADR-027 (layered CI images)
