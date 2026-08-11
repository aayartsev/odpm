# Shared wheel cache (pip / uv)

From **4.7+**, odpm can share a pip/uv **download cache** across projects on one host. This is not a shared `.venv`: each project still has its own `site-packages`. The cache speeds up reinstalling the same wheels for the same Python.

See also [golden core venv](golden-venv.md) (reusing a prebuilt core `.venv`).

## Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `ODPM_WHEEL_CACHE_ROOT` | Host root for the shared cache | `~/.odpm/cache` |
| `PIP_CACHE_DIR` | If set explicitly, odpm does **not** override it | `{root}/wheels/<python_version>` |
| `UV_CACHE_DIR` | If set explicitly, odpm does **not** override it | `{root}/uv` |

Values are merged as: layered `.env` (`~/.odpm/.env` → project `.env`) as the base, with the **process environment overriding** dotenv. Host mounts use that merge when generating compose; inside the container cache paths are `/cache/odpm/...` (mount). `ODPM_GOLDEN_VENV` from dotenv is injected into the `odoo` service environment. See [env-dotenv.md](env-dotenv.md).

## Host layout

```text
${ODPM_WHEEL_CACHE_ROOT:-~/.odpm/cache}/
├── uv/
└── wheels/
    ├── 3.10/
    ├── 3.11/
    ├── 3.12/
    └── 3.13/
```

Inside the container (developer / server) the same directories are mounted at:

- `PIP_CACHE_DIR=/cache/odpm/wheels/<python_version>`
- `UV_CACHE_DIR=/cache/odpm/uv`

The per-project `data/odoo/home/.../.cache` mount remains for other data; the wheel cache is a separate global mount.

## When it applies

| Scenario | Behaviour |
|----------|-----------|
| `developer` / `server` | Env + compose mounts under `/cache/odpm/...` |
| `ci` (baked) | Host-side bake reads `ODPM_WHEEL_CACHE_ROOT` from layered dotenv + process env; no mount (venv is already in the image). Download cache inside `docker build` needs a BuildKit cache mount — separate. |

## Fleet / shared workers

On a worker, set in `~/.odpm/.env`:

```ini
ODPM_WHEEL_CACHE_ROOT=/var/cache/odpm
```

The directory must be writable by the container runtime user (often `9999:9999` / `odoo`) or a shared docker group with `chmod 2775`.

## Disable / override

- Set your own `PIP_CACHE_DIR` / `UV_CACHE_DIR` — odpm will leave them alone.
- Leave `ODPM_WHEEL_CACHE_ROOT` unset to use `~/.odpm/cache`.
