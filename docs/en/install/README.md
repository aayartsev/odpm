# Installing odpm

Choose how to install **odpm** on the host (not the same as deploying an Odoo project with `odpm --init`).

| Platform | Recommended method | Article |
|----------|-------------------|---------|
| Debian / Ubuntu | `.deb` package, APT repository | [linux-deb.md](linux-deb.md) |
| Fedora / RHEL | `.rpm` package, DNF repository | [fedora-rpm.md](fedora-rpm.md) |
| macOS | pipx (no native `.pkg` yet) | [macos-pipx.md](macos-pipx.md) |
| Windows | WSL2 + Docker Desktop | [windows-wsl.md](windows-wsl.md) |
| Any OS / odpm development | pip, editable, `odpm.py` | [pip-legacy.md](pip-legacy.md) |

## Host requirements for project work

After installing odpm, [local development](../getting-started/local-dev-from-scratch.md) usually requires **Docker** and **git** (see your platform article).

Prebuilt `.deb` and `.rpm` packages are published on [GitHub Releases](https://github.com/aayartsev/odpm/releases) and in CI artifacts from the **Release packages** workflow after pushes to `4.0-beta` / `4.0-rc1` / `main`.

## Next

[Local dev from scratch](../getting-started/local-dev-from-scratch.md)
