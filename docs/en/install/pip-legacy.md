# pip install and running from source

For odpm contributors or systems without ready-made `.deb` / `.rpm` packages.

## pip / editable

Requires **Python 3.10+**. On Linux with [PEP 668](https://peps.python.org/pep-0668/), use a venv or [pipx](https://pipx.pypa.io/), not system-wide `pip install`.

```bash
pip install /path/to/odpm
# for odpm development:
pip install -e /path/to/odpm
odpm --version
```

The `odpm` command loads templates from the installed `dev_project` package.

## Run without installing the package

Copy `odpm.py` and the `dev_project/` directory, or clone the full repository:

```bash
python3 /path/to/odpm/odpm.py --version
```

Both approaches are supported.

Full install table: [Installing odpm (all platforms)](README.md).
