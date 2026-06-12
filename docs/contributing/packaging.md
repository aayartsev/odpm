# Packaging

Workflow: [`.github/workflows/release-packages.yml`](../../.github/workflows/release-packages.yml)

## deb

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

Пользовательская установка: [install/](../install/linux-deb.md), [pip (legacy)](../install/pip-legacy.md).
