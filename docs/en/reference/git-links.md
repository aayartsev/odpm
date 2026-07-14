# Repository links and local directories

> **AI-translated** from Russian.

Such links are used in **`developing_project`**, in **`dependencies`**, in **`odoo_git_link`**, in **`service_sources`** (manifest v2), and in the **`--init`** parameter.

## Three ways to specify a code source

| Method | Example | When to use |
|--------|---------|-------------|
| **HTTPS** | `https://github.com/org/repo.git` | Public repositories, machines without an SSH key |
| **SSH** | `git@github.com:org/repo.git` | Day-to-day work, private repositories |
| **Local directory** | `file:///home/user/my_addons` | Code only on disk, no remote git |

After the address, separated by a **space**, you may specify a **branch** and optionally a **commit**:

```text
git@github.com:org/odoo.git 19.0
git@github.com:org/odoo.git 19.0 a1b2c3d4e5f6789abcdef0123456789abcdef012
```

## Why `file://` has three slashes in a row

A file address in URL notation is: **scheme**, **colon**, **two slashes**, then **path**.

- `file://` — “file on disk” scheme (two slashes after the colon is normal for URLs).
- On Linux and macOS an **absolute** path starts with `/`.
- The result is **`file://` + `/home/user/project`** = **`file:///home/user/project`** — **three** slashes in a row.

This is not a typo. `file://home/user` **without** the third slash for an absolute path on Unix is **wrong**.

On WSL on Windows, for directories inside Linux use the same form: `file:///home/user/...`.

## How odpm processes a link

| Type | odpm action |
|------|-------------|
| HTTPS, SSH, git@ | Clone into **`ODOO_PROJECTS_DIR`** from `.env`, then select branch/commit per version pinning rules |
| `file://` | **No clone** — the directory is used **as-is** at the given path |

For `file://`, the lock file stores a **content fingerprint** of the directory, not a git hash — a remote repository is more reliable for shared builds.

## `${VAR}` in manifest links

In `odpm.json` and in `developing_project` you can write paths and hosts via variables so **one** manifest in git fits different machines:

```json
"odoo_git_link": "file://${ODOO_PLATFORM_DIR}",
"dependencies": ["file://${OCA_WEB_PATH}"],
"developing_project": "file://${DEVELOPING_PROJECT_DIR}"
```

Values are set in the project `.env` or in the process environment (CI). After expansion odpm works with a normal `file://` or git URL. Details: [odpm.json](odpm-json.md), [`.env` variables](env-dotenv.md).

## Where to specify in configuration

- **Developing project:** `--init <link>` or `developing_project` in `user_settings.json`.
- **Odoo platform:** `odoo_git_link` in `odpm.json` or `--odoo-git-link` at initialization.
- **Dependencies:** `dependencies` array in `odpm.json`.
- **Sidecar / build contexts (v2):** `service_sources` object in `odpm.json` — see [service-sources.md](service-sources.md).

## Practical tips

- For a team in shared git, store **remote repository addresses**, not `file://`.
- `file://` — for local work, a monorepo, or code not published to a server.
- For private GitHub/GitLab, configure SSH (`~/.ssh/config`); `PATH_TO_SSH_KEY` in `.env` — only when standard SSH is unavailable (often on a build machine).
