# Team coordinator role

> **AI-translated** from Russian.

In small and medium Odoo teams it helps to designate a **coordinator** (lead developer or infrastructure owner) who maintains **project manifest integrity** and **dependency version pinning**. Other developers mainly work on their module branches without silently changing the stack.

## Division of responsibilities

| Artifact | Coordinator | Regular developer |
|----------|---------------|-------------------|
| `odpm.json` | Changes dependencies, Python/Odoo/PostgreSQL versions | Reads, does not fork the stack locally |
| `.odpm/deps.lock.json` | Updates after agreement (`--update-lock`), commits | Gets from git, builds from the lock |
| `developing` field in lock | Pins for server and build | In `developer` scenario their branch does **not** forcibly match the lock |

## How to change a dependency

1. Discussion and pull request with changes to `dependencies`, `requirements_txt`, or `oca_dependencies.txt`.
2. On the coordinator's machine: `odpm --update-lock --skip-start`.
3. Commit the **lock file** together with the manifest changes.
4. In automated checks: `odpm plan --strict`.

## Local `file://` paths and the team

A `file:///...` reference is convenient for **one** developer on their own disk. For shared builds and team sync, **remote git** is more reliable. For a local platform, the lock records a directory fingerprint, not a commit hash — details in [deps.lock.json](../reference/deps-lock.md).

If git stores a manifest with `${VAR}` (e.g. `file://${ODOO_PLATFORM_DIR}`), the coordinator lists **required** variables in the project README, project `.env.example`, or CI instructions. Values are not committed in `odpm.json` — only in `.env` (locally) or runner secrets / `export` (CI).

## Common language — `odpm plan`

The team sees the same preparation plan:

```bash
odpm plan --skip-start
odpm plan --plan-show-diff --skip-start
odpm plan --plan-strict --skip-start
```

This reduces "my compose is different" disputes before release.
