# Configuration hierarchy

> **AI-translated** from Russian.

Several configuration sources act **at the same time**. It is important to understand **what overrides what** so you do not look for a parameter “in the wrong place”.

## Precedence (strongest to weakest)

```text
Command-line parameters for a single run
    ↓
odpm.json and user_settings.json (files in the project directory / in git)
    ↓  (in whitelist strings: ${VAR} ← process env, then project .env)
project .env file
    ↓
~/.odpm/.env file (shared user profile)
    ↓
shell environment variables (when creating .env without prompts)
    ↓
odpm built-in defaults
```

## One .env file at a time

odpm reads **either** `.env` in the project directory **or** `~/.odpm/.env` — **not both at once**. If the project directory has its own `.env`, the global file **does not supplement** it: a key missing in the project **is not** pulled from `~/.odpm/.env`.

Timing exception: before full initialization, only the project `.env` may be read for early checks (see [message locale](locale.md)).

## Generated files

`docker-compose.yml`, `.odpm/runtime/config.json`, `.odpm/database/last_run.json`, and the root `.dockerignore` are **generated** by odpm from the project description and scenario. Do not treat them as the place for “manual truth” — see [generated files](generated-files.md) and [PostgreSQL state](database-state.md).

## Git version pinning

When working with repositories: `--no-git-update` overrides `--update-lock`, then the existing lock file, then branch tip / nightly date. Details: [deps.lock.json](deps-lock.md).
