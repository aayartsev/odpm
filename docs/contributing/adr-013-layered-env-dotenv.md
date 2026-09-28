# ADR-013: Layered host `.env` (home + project) (4.7)

**Status:** accepted (4.7.0-dev)  
**Date:** 2026-06-27

## Context

odpm host settings (ports, scenario, backup paths, git clone roots, debugger, compose prefix) live in a **`.env`** file. Two locations are supported:

| Path | Typical role |
|------|----------------|
| `~/.odpm/.env` | User-wide defaults shared across odpm projects |
| `<project_dir>/.env` | Per-environment overrides (ports, `ODPM_COMPOSE_PREFIX`, manifest `${VAR}` helpers) |

Until 4.6, documentation described a **single active file**: if project `.env` exists, `~/.odpm/.env` is **not read at all**. Missing keys in a partial project `.env` are not filled from home (and required keys such as `BACKUP_DIR` can fail at parse time).

The configuration hierarchy diagram in [config-hierarchy.md](../reference/config-hierarchy.md) already lists project `.env` **above** `~/.odpm/.env`, but the prose contradicted that order.

Goal (4.7 track C): **layered read** — home provides a base profile; project **shadows** individual keys. Enables storing shared paths in one place and project-specific settings (e.g. `ODPM_COMPOSE_PREFIX` from [ADR-012](adr-012-compose-service-prefix.md)) in the project directory without duplicating the full `.env`.

## Decision

### Read path: layered merge

Host helper: `load_layered_dotenv_dict(project_path, config_home_dir) -> dict[str, str]`.

1. Load `~/.odpm/.env` when the file exists (base layer).
2. Load `<project_path>/.env` when the file exists (overlay layer).
3. For each key, **project wins** on collision.

`CreateUserEnvironment.parse_env_file()` uses the merged dict for `parse_dotenv_dict()` and stores it in `_project_dotenv` (effective dotenv for runtime).

**Priority for a key's final value** (strongest first):

```text
os.environ          (manifest ${VAR} only, via EnvResolver)
    ↓
project .env        (overlay)
    ↓
~/.odpm/.env        (base)
    ↓
defaults in parse_dotenv_dict (ports, scenario, …)
```

Custom keys used only for `${VAR}` in `odpm.json` / `user_settings.json` (e.g. `ODOO_PLATFORM_DIR`, `GIT_HOST`) follow the **same** file merge; they are not a separate category.

### Write path: unchanged

`resolve_env_file_path()` keeps **4.6 semantics** — primary **write** target for the interactive wizard and non-interactive first-run creation:

| Condition | Write target |
|-----------|----------------|
| `<project_path>/.env` exists | Project file |
| Else | `~/.odpm/.env` |

The wizard does **not** auto-split or copy home keys into project `.env`. Users who want overrides add only differing keys to project `.env`.

`CreateUserEnvironment.env_file` remains the resolved **write** path, not the sole read source.

### Early locale bootstrap

`bootstrap_host_locale()` (before full pipeline, [locale.md](../reference/locale.md)) applies the same layered lookup for `ODPM_LOCALE` so a locale set only in `~/.odpm/.env` is honoured when the project file omits it.

### Non-interactive first run

`has_noninteractive_env_configuration()` returns true when **either** `.env` file exists (or required keys are in `os.environ`), so CI can rely on a home-only profile.

### Backward compatibility

| Setup | 4.6 behaviour | 4.7 behaviour |
|-------|---------------|---------------|
| Full project `.env` only | Unchanged | Unchanged (project overlay is complete) |
| Home `.env` only | Unchanged | Unchanged |
| Both files, disjoint keys | Home ignored | **Merged** — home fill-in for missing project keys |
| Both files, same key | Project value only (home never read) | Project value only |

No new `.env` variable is introduced. No manifest `requires_odpm` bump.

### Implementation map (track C)

| Phase | Module | Change |
|-------|--------|--------|
| C1 | `dev_project/host/user_env_parse.py` | `layered_env_paths`, `load_layered_dotenv_dict`; `has_noninteractive_env_configuration` |
| C1 | `dev_project/host/user_env.py` | `parse_env_file()` calls layered load |
| C2 | `dev_project/host/locale_bootstrap.py` | Layered `ODPM_LOCALE` |
| C3 | `docs/reference/config-hierarchy.md`, `env-dotenv.md` | Replace «one file at a time» with layered read |
| C4 | `tests/test_user_env_bootstrap.py`, `test_odpm_locale_env.py`, `test_env_substitution.py` | Merge matrix T1–T9 |

`EnvResolver.from_user_env()` continues to use `project_dotenv_dict()`; no API change once merged dict is stored.

## Consequences

- **Positive:** Less duplication across odpm projects; partial project `.env` (e.g. only `ODPM_COMPOSE_PREFIX`) works with a shared home profile.
- **Positive:** Code aligns with the hierarchy diagram in user docs (after C3).
- **Neutral:** `resolve_env_file_path()` tests remain valid (write semantics).
- **Caution:** Sensitive values in `~/.odpm/.env` apply to all projects unless overridden in project `.env`.

## References

- Plan: `.cursor/plans/4.7_env_layering_bf783c4c.plan.md`
- [ADR-012](adr-012-compose-service-prefix.md) — typical per-project override in `.env`
- [ADR-014](adr-014-compose-stack-network.md) — shared external network in `~/.odpm/.env` (e.g. `ODPM_COMPOSE_NETWORK=proxy`)
- [config-hierarchy.md](../reference/config-hierarchy.md), [env-dotenv.md](../reference/env-dotenv.md)
