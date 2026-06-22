# Installing odpm

!!! info "Use stable for production"
    For production, read **[stable](https://aayartsev.github.io/odpm/stable/en/install/)** docs (currently odpm **4.4.3**) and the APT/YUM **`stable`** suite.
    Archived pre-releases: [4.4.3-beta](https://aayartsev.github.io/odpm/4.4.3-beta/en/install/), [4.4.2-beta](https://aayartsev.github.io/odpm/4.4.2-beta/en/install/).
    See [Which docs to read](../getting-started/documentation-versions.md).

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

Prebuilt `.deb` and `.rpm` packages are published on [GitHub Releases](https://github.com/aayartsev/odpm/releases) (`v*` tags) and mirrored to APT/YUM on [GitHub Pages](https://aayartsev.github.io/odpm/apt/) after the release CI run.

## Next

[Local dev from scratch](../getting-started/local-dev-from-scratch.md)
