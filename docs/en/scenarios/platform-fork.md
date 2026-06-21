# Custom Odoo platform repository

> **AI-translated** from Russian.

If the organization maintains its **own fork** of Odoo core (not only the official `github.com/odoo/odoo`), it is connected via project manifest fields.

## Fields in `odpm.json`

| Field | Meaning |
|-------|---------|
| `odoo_git_link` | Git URL of the platform repository; branch and commit can be specified after a space |
| `platform_name` | Python package name of the fork (default `odoo`); affects conf file name and launch command |
| `odoo_version` | Must match the branch in the platform repository |
| `python_version`, `distro_name`, `distro_version` | Compatible with fork requirements |

Configuration file name: **`{platform_name}.conf`** (not necessarily `odoo.conf`).

## Example at initialization

```bash
odpm --init https://github.com/aayartsev/odoo_demo_project.git --branch 19.0 \
  --odoo-version 17.0 \
  --odoo-git-link 'git@github.com:org/odoo-17.git 17.0' \
  --platform-name odoo \
  --python-version 3.10 --distro-version 12
```

## Nightly builds and commit date

The `odoo_build_date` field or `--odoo-build-date` parameter (format `YYYYMMDD`) selects which commit on the platform branch to take "as of end of that day". Not applied if the link already pins a commit hash.

## Dependencies with nested `odpm.json`

With `use_oca_dependencies` enabled, odpm reads manifests in nested repositories. Odoo/Python version incompatibility with the main project: warning in developer mode, **error** in the `ci` scenario. The **host** platform repository is not replaced.

See [repository links](../reference/git-links.md), [odpm.json](../reference/odpm-json.md).
