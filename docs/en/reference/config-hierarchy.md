# Configuration hierarchy

> **AI-translated** from Russian.

Several configuration sources act **at the same time**. It is important to understand **what overrides what** so you do not look for a parameter “in the wrong place”.

## Precedence (strongest to weakest)

```text
Command-line parameters for a single run
    ↓
odpm.json and user_settings.json (files in the project directory / in git)
    ↓  (in whitelist strings: ${VAR} ← process env, then effective .env: project over ~/.odpm/.env)
project .env file (overlay)
    ↓
~/.odpm/.env file (user base profile)
    ↓
shell environment variables (when creating .env without prompts)
    ↓
odpm built-in defaults
```

## Two `.env` layers on read (4.7)

On **read**, odpm merges both files when present:

1. `~/.odpm/.env` — base (shared paths, SSH, locale, defaults for all projects).
2. `.env` in the odpm environment directory — **overlay**; matching keys **override** home.

The effective dict drives ports, scenario, manifest `${VAR}`, and early `ODPM_LOCALE` (see [message locale](locale.md)). Details: [env-dotenv.md](env-dotenv.md), [ADR-013](https://github.com/aayartsev/odpm/blob/4.7.0-dev/docs/contributing/adr-013-layered-env-dotenv.md).

On **write** (first-run wizard, non-interactive create) the **primary** target is unchanged: project `.env` if it already exists, else `~/.odpm/.env`. odpm does **not** auto-copy home into project — put only differing keys in project `.env`.

| Setup | Behaviour |
|-------|-----------|
| Home only | Same as before when no project `.env` |
| Full project only | Same as before with a complete project `.env` |
| Both, disjoint keys | Merge: home fill-in + project overrides |
| Both, same key | Value from project `.env` |

## Generated files

`docker-compose.yml`, `.odpm/runtime/config.json`, `.odpm/database/last_run.json`, and the root `.dockerignore` are **generated** by odpm from the project description and scenario. Do not treat them as the place for “manual truth” — see [generated files](generated-files.md) and [PostgreSQL state](database-state.md).

## Git version pinning

When working with repositories: `--no-git-update` overrides `--update-lock`, then the existing lock file, then branch tip / nightly date. Details: [deps.lock.json](deps-lock.md).
