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
python -m build
pip install dist/odpm-*.whl
```

Артефакты: GitHub Releases и Actions artifact `release-packages` (deb + rpm). Release на GitHub — только при tag `v*`.

Пользовательская установка: [install/](../install/linux-deb.md).
