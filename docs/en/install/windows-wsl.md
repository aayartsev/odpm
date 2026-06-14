# Windows (WSL)

On Windows, odpm runs via **WSL2** and Docker Desktop.

## Step-by-step guide

Detailed walkthrough with screenshots:

**[Odoo development environment setup in WSL](https://blog.yartsev.by/odoo_tutorials/001_config_development_environment/004_odoo_development_in_wsl.html)**

## Short version

1. Install **WSL2** (Ubuntu recommended).
2. Install **Docker Desktop** with WSL integration.
3. In a WSL terminal, install odpm — [.deb](linux-deb.md) or [pip](pip-legacy.md).
4. Keep the project directory and run `odpm --init` on the Linux filesystem (`/home/...`), not on `C:\` via `/mnt/c` when possible — bind mounts are faster in Docker.
5. VS Code: **WSL** extension, open the folder inside WSL.

## `file://` links

In WSL use Linux paths:

```text
file:///home/user/my_addons
```

Three slashes after `file:` — see [git-links.md](../reference/git-links.md).

Full install table: [Installing odpm (all platforms)](README.md).
