# Packaging

Workflow: [`.github/workflows/release-packages.yml`](../../.github/workflows/release-packages.yml)

## Version axes

| Constant / artifact | Example | Meaning |
|---------------------|---------|---------|
| `RELEASE_VERSION` | `4.3-rc1` | Git tag (`v4.3-rc1`), deb/rpm filenames, GitHub Release title |
| `ODPM_VERSION` | `4.0` | `odpm.json` → `odpm_version`, `odpm --version`, pip wheel metadata |

Bump `RELEASE_VERSION` in `dev_project/constants/scenarios.py` and sync `debian/changelog` + `packaging/odpm.spec` for each native package release.

## deb

### APT repository (recommended)

Published on tag builds to `https://aayartsev.github.io/odpm/apt/` (`stable` / `testing` suites).

GitHub Actions secrets:

| Secret | Purpose |
|--------|---------|
| `APT_REPO_GPG_PRIVATE_KEY` | Sign `Release` / `InRelease` |
| `APT_REPO_GPG_PASSPHRASE` | Key passphrase |

Public keyring: `packaging/apt/odpm-archive-keyring.gpg` (binary, for `signed-by=`). Maintainer notes: [`packaging/apt/README.md`](../../packaging/apt/README.md).

User install: [install/README.md](../install/README.md) (hub), [install/linux-deb.md](../install/linux-deb.md) (Debian).

### Local / manual .deb

```bash
./scripts/build_deb.sh
sudo apt install ./dist/odpm_*_all.deb
```

## rpm

```bash
./scripts/build_rpm.sh
sudo dnf install ./dist/odpm-*.rpm
```

## pip / wheel

```bash
pip install build
python -m build
pip install dist/odpm-*.whl
odpm --version
```

Runtime dependency: `packaging` (declared in `pyproject.toml`; Debian package uses `python3-packaging`).

### PyPI publish (maintainers)

Workflow: [`.github/workflows/publish-pypi.yml`](../../.github/workflows/publish-pypi.yml)

- **Manual only** — `workflow_dispatch` with `confirm_publish=true` (no automatic upload on tag).
- Default target: **TestPyPI** (`use_testpypi=true`); production PyPI requires `use_testpypi=false` and configured secrets.
- GitHub Environment `pypi` + secrets `TEST_PYPI_API_TOKEN` / `PYPI_API_TOKEN` (or OIDC trusted publishing when enabled).

Артефакты: GitHub Releases и Actions artifact `release-packages` (deb + rpm). Release на GitHub — только при tag `v*`.

Пользовательская установка: [install/README.md](../install/README.md), [pip (legacy)](../install/pip-legacy.md).
