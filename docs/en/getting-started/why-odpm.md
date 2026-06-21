# Why odpm: problems it solves

> **AI-translated** from Russian.

For **all roles** — developer, team coordinator, DevOps, beginner. Short on-ramp and host install: [Beginner-friendly guide](beginner-friendly.md). Team scaling and scenarios: [scaling](../scenarios/scaling.md), [team-coordinator](../scenarios/team-coordinator.md).

---

## Who this is for

| Role | Why read |
|------|----------|
| **Developer** | Understand why “Odoo is installed” ≠ a ready workspace |
| **Coordinator / lead** | Justify a single `odpm.json` and lock in git |
| **DevOps / CI** | Connect developer/server/ci without three different scripts |
| **Odoo beginner** | Full picture before [first project](local-dev-from-scratch.md) |

---

## North Star

> **You commit `odpm.json` → a colleague clones the project → the same Odoo stack with addons, Python, DB, and debugger — on laptop, server, and CI.**

**odpm** is not “another way to install Odoo”, but a **reproducible environment manager** from a declarative manifest (`odpm.json`) that lives in the project repo.

---

## Pain by layer

### 1. “Odoo runs” ≠ “ready to develop”

A system package, bare `docker run odoo:19`, or a long wiki gives a **running service** — not the same as a **developer workspace**. Building one means answering:

- where **your** code lives and how it enters `addons_path`;
- where **core sources** are for reading, debugging, and LSP;
- where **OCA and corporate repos** are and which branches they use;
- which **Python/venv** and **pip deps** the project needs;
- which **odoo.conf** ties it together.

**Without odpm** — manual glue or a toolbox of tools on every Odoo version, machine, or project change. **With odpm** — the whole contour in **one project directory** from one stack manifest.

### 2. Multi-repo and paths — “module not found”

A mature Odoo project is platform + developing + N dependencies. Typical pains:

- forgotten directory in `addons_path`;
- different paths on host vs container;
- symlinks, subprojects, OCA `oca_dependencies.txt`;
- “works on my machine” due to local folder layout.

**With odpm** — centralized resolver, `map_folders`, nested `odpm.json`, [`deps.lock.json`](../reference/deps-lock.md), `${VAR}` substitution in manifests for local paths without forking json in git.

### 3. Mixed OS and CPU architectures in distributed teams

**Without odpm / per-machine guides:**

- separate playbooks: Ubuntu, Fedora, macOS, Windows (WSL), Apple Silicon;
- paths (`/home/...` vs `C:\` vs `/Users/...`), shell, permissions, line endings;
- Python/pip and native wheels for **each** host architecture;
- “works on Linux” — different failure on macOS or ARM;
- CI on amd64, laptop on arm64 — image and binary surprises;
- onboarding = “figure out your OS, then open the right wiki branch”.

**With odpm:**

- one `odpm.json` in git — **one** stack for the team;
- machine-specific bits in [`.env`](../reference/env-dotenv.md), not wiki forks;
- `arch` in manifest and lock venv for CPU; CI image for target platform;
- installing **odpm itself** on Linux / macOS / WSL — without a separate “how to run Odoo” per OS.

**Honest boundary:** arm64 Mac and amd64 CI do not magically match; Apple Silicon may need multi-arch images or same-arch builders. **Rules** (manifest, compose, lock, scenarios) stay shared — see [scaling](../scenarios/scaling.md).

Docker (next section) is the usual answer to §3 — but a container alone does not fix orchestration.

### 4. Docker doubles complexity without an orchestrator

Teams use Docker so Ubuntu/macOS/Windows look the same **inside the image**. **Without an orchestrator**, Docker **moves** complexity elsewhere:

- bind mounts for platform/developing/deps;
- UID/GID and file permissions;
- compose + PostgreSQL + ports;
- pip packages **inside** the container;
- debugger for in-container processes.

**With odpm** (orchestrator on top of Docker):

- on the host — Docker, git, odpm; **one** launch flow on any desktop OS;
- Odoo stack (Debian image, Python, venv, postgres, compose) **in the container** from one `odpm.json`;
- auto-generated compose, Dockerfile, odoo.conf, volume mapping, debugger setup, and the rest of the “docker layer”.

### 5. “Everyone has their own setup” — team pain

**Without a shared manifest:**

- Python 3.10 vs 3.12 across laptops;
- different OCA dependency states;
- different postgres/debugger bootstrap;
- onboarding = long checklist.

**With odpm** — split **team** ([`odpm.json`](../reference/odpm-json.md) + lock in git) vs **personal** ([`user_settings.json`](../reference/user-settings.md), per-machine `.env`). Coordinator pins the stack; others reproduce it. See [config split](../reference/config-split.md).

### 6. Three roles — one engine

One codebase, different behavior via [`ODPM_SCENARIO`](../reference/env-dotenv.md):

| Role | Pain without odpm | What odpm gives |
|------|-------------------|-----------------|
| **Developer** | long per-machine setup | [`developer`](../scenarios/developer.md): full dev toolkit, debugger, CLI, VS Code and PyCharm |
| **Server / VM** | separate project wiring | [`server`](../scenarios/server.md): same stack, no dev utilities, postgres on localhost |
| **CI** | separate build scripts | [`ci`](../scenarios/ci.md): baked image with the same rules as the team |

One pipeline; scenario selects the profile — not three unrelated tools.

### 7. Unpredictable re-setup

**Without odpm** (custom scripts, ansible, manual compose):

- unclear what is hand-edited vs regenerated;
- re-setup overwrites `docker-compose.yml`, Dockerfile, or config;
- no dry-run — surprises after the fact;
- no shared “generated vs source of truth” list.

**With odpm:**

- [`odpm plan`](../reference/cli.md) — preview steps and diff before materialize;
- [generated files](../reference/generated-files.md) catalog;
- templates in `.odpm/` vs root artifacts (compose, runtime config);
- one manifest describes stack composition.

### 8. Operational tasks scattered across tools

Beyond “start Odoo”, daily work needs:

- DB restore from archive;
- new DB with language/country/demo;
- admin password reset;
- module install/update (`-i` / `-u`);
- pre-commit in the container;
- module secrets without committing to git.

**With odpm** — one CLI orchestrator around one compose stack ([CLI reference](../reference/cli.md), [secrets](../operations/secrets.md)).

### 9. IDE and debugging

**Without odpm:** manual `launch.json`, host/container path mappings, Pylance `extraPaths`, PyCharm/pydevd compatibility.

**With odpm:** `debug-profile.json`, generated VS Code / PyCharm configs, `debugpy` and `odoo-stubs` in developer scenario. See [IDE debugging](../operations/vscode-debug.md).

### 10. CI and reproducible builds

**Without odpm:**

- different pip/venv on CI;
- dependencies without pinned SHAs;
- ad-hoc image builds.

**With odpm:** [`deps.lock.json`](../reference/deps-lock.md), `--update-lock`, CI image bake from commit hashes. See [ci scenario](../scenarios/ci.md).

---

## Where odpm sits on the map

Niche **between** “plain Docker Odoo” and **heavy Doodba / Odoo.sh**:

| Alternative | What typical teams still miss |
|-------------|------------------------------|
| Package / bare metal | multi-repo, Docker, IDE, CI profile |
| Official Odoo Docker | developing project, git deps, venv, debug |
| Dev Containers | Odoo-specific: odpm.json, OCA graph, lock, scenarios |
| Doodba | higher DevOps bar; less “one button for beginners” |
| Odoo.sh | SaaS, not self-hosted laptop |

**odpm** — Odoo-specific dev environment manager: declarative manifest + scenario + plan + container contract, no cloud lock-in.

---

## What odpm deliberately does not solve

- **Not a PaaS** — no Odoo.sh-style staging/prod.
- **Not full production hardening** — [`server`](../scenarios/server.md) is a profile; nginx/TLS/backup is on you ([security](../operations/security.md)).
- **Not a substitute for learning Odoo** — framework, ORM, modules still require study.
- **Plugins/hooks** — in development; Doodba-style `custom/` hooks are **not** fully covered today.
- **Not byte-identical reproducibility** (like Nix) — **practical** reproducibility via lock + image + manifest.

---

## Next steps

1. [Beginner-friendly guide](beginner-friendly.md) — host install and first run.
2. [Local dev from scratch](local-dev-from-scratch.md) — `odpm --init`, first database.
3. [Team coordinator](../scenarios/team-coordinator.md) — lock, non-interactive, CI.
4. [Developer scenario](../scenarios/developer.md) — debugging and `dev_mode`.

---

## In short

> Odoo development breaks on **infrastructure**, not Python syntax: multi-repo, paths, mixed OS and architectures, Docker, venv, config, IDE, CI. odpm turns that into **one reproducible project contour** from `odpm.json` so the team spends time on modules, not rebuilding the environment.
