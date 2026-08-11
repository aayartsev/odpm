# Golden core venv

From **4.7+**, in fresh scenarios (`developer`, `server`) odpm can reuse a **core** virtualenv (bootstrap + `odoo/requirements.txt` + implicit packages) keyed by `venv_lock_hash`. Project extras (`requirements_txt`, debugpy, stubs) still go through `sync_extras_requirements` and are not part of the golden store.

This complements the [shared wheel cache](wheel-cache.md) (downloads). CI `baked` does **not** use golden: the image already contains its `.venv`.

## Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `ODPM_GOLDEN_VENV` | `0` / `false` — disable golden | enabled (`1`) |
| `ODPM_GOLDEN_VENV_ROOT` | Host directory for templates (mounts) | `~/.odpm/venvs` |

`ODPM_GOLDEN_VENV` from layered `.env` / process env is injected into the `odoo` service `environment` when compose is generated, so `ODPM_GOLDEN_VENV=0` in `~/.odpm/.env` disables golden inside the container. `ODPM_GOLDEN_VENV_ROOT` affects the host mount (via dotenv + process env merge).

While a template is being written, the golden directory has an `.incomplete` marker — `golden_exists` and clone ignore it; `.lock` is written only after freeze/meta.

## Layout

```text
${ODPM_GOLDEN_VENV_ROOT:-~/.odpm/venvs}/
└── <venv_lock_hash>/
    ├── .venv/                          # core-only
    ├── .lock
    ├── meta.json
    └── core-requirements.freeze.txt
```

Inside the container the directory is mounted at `/cache/odpm/venvs` (developer/server).

## Recreate behaviour

1. If a golden for the current `venv_lock_hash` exists — clone into the project `.venv` (`clonevirtualenv`, otherwise install from freeze + hardlink/wheel cache).
2. Otherwise — `install_core_fresh`, then populate the golden store.
3. Always — `sync_extras_requirements`.

## Fleet

On a worker, in `~/.odpm/.env`:

```ini
ODPM_GOLDEN_VENV_ROOT=/var/lib/odpm/venvs
ODPM_WHEEL_CACHE_ROOT=/var/cache/odpm
```

Permissions: container runtime user (`9999:9999` / `odoo`) or a shared group.

## Disable

```ini
ODPM_GOLDEN_VENV=0
```

Restores core install via `install_core_fresh` without the store.
