# Fedora / RHEL (.rpm)

Recommended on Fedora 41+.

```bash
./scripts/build_rpm.sh
sudo dnf install ./dist/odpm-*.rpm
odpm --version
```

## Dependencies

- **Requires:** `python3-packaging`, `git`
- **Recommends:** `moby-engine` / `docker`

Installs `/usr/bin/odpm` and `dev_project` under `python3/site-packages`.

Packages are also on [GitHub Releases](https://github.com/aayartsev/odpm/releases) and in the `release-packages` workflow.

Full install table: [Installing odpm (all platforms)](README.md).
