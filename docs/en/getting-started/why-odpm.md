# Why odpm: problems it solves

> **AI-translated** from Russian.

For **all roles** — developer, team coordinator, DevOps, beginner. Short first-run guide and host install: [Beginner-friendly guide](beginner-friendly.md). Team scaling and scenarios: [scaling](../scenarios/scaling.md), [team-coordinator](../scenarios/team-coordinator.md).

---

## Who this is for

| Role | Why read |
|------|----------|
| **Developer** | Understand why “Odoo is installed” ≠ a ready workspace |
| **Coordinator / lead** | Justify a single `odpm.json` and lock in git |
| **DevOps / CI** | Connect developer/server/ci without three different scripts |
| **Odoo beginner** | Full picture before [first project](local-dev-from-scratch.md) |

---

## Main goal

> **You shape `odpm.json` in the repository → a colleague clones the project → the same Odoo stack with addons, Python, DB, and debugger — on laptop, server, and CI.**

**odpm** is not “another way to install Odoo”, but a **reproducible environment manager** from a declarative manifest (`odpm.json`) that is part of the project.

---

## Problems by layer

### 1. “Odoo runs” ≠ “ready to develop”

A system package, bare `docker run odoo:20`, or a long wiki gives a **running service** — but that is not the same as a **developer workspace**. Building one means answering:

- where **your** code lives and how it enters `addons_path`;
- where **core sources** are for reading, debugging, and LSP;
- where **OCA and corporate repos** are and which branches they use;
- which **Python/venv** and **pip deps** the project needs;
- which **odoo.conf** ties it together.

**Without odpm** — either manual glue or a whole toolbox of tools on every Odoo version, machine, or project change. **With odpm** — the whole contour lives in **one project directory** and is configured from a single stack description.

### 2. Multi-repo and paths — “module not found”

A mature Odoo project is not one git repository, but **platform + developing + N dependencies**. Typical pains:

- forgotten directory in `addons_path`;
- different paths on host vs container;
- symlinks, subprojects, OCA `oca_dependencies.txt`;
- “works on my machine” because of how modules or the platform are laid out locally.

If you use **odpm**, you get a centralized alignment mechanism, `map_folders`, nested `odpm.json`, [`deps.lock.json`](../reference/deps-lock.md), and `${VAR}` substitution in the manifest for local paths without forking the json in git.

### 3. Mixed OS and CPU architectures in distributed teams

**Without odpm / per-machine guides:**

- separate playbooks: Ubuntu, Fedora, macOS, Windows (WSL), Apple Silicon;
- paths (`/home/...` vs `C:\` vs `/Users/...`), shell, permissions, line endings;
- Python/pip and native wheels for **each** host architecture;
- “works on Linux on x86” — a colleague on macOS on ARM hits a different error;
- CI runs on amd64 while the developer laptop is arm64 — surprises when building images or binary dependencies;
- onboarding = “figure out your OS, then open the right wiki branch”.

With **odpm:**

- one `odpm.json` in git — **one** stack composition for the whole team;
- machine-specific bits in [`.env`](../reference/env-dotenv.md), not another wall of wiki text;
- `arch` in the manifest and lock venv account for CPU; the CI image is built for the target platform;
- it boils down to installing **odpm itself** on Linux / macOS / WSL — without a separate “how to run Odoo” guide per OS.

**Honest boundary:** arm64 on Mac and amd64 on CI do not resolve themselves; Apple Silicon may need multi-arch images or a same-architecture builder. **Rules** (manifest, compose, lock, scenarios) stay shared — see [scaling](../scenarios/scaling.md).

The usual answer to this pain is **Docker** (next section): one runtime inside the container. Without an orchestrator, the container alone does not close the gap.

### 4. Docker doubles complexity without an orchestrator

To ease §3, teams move to Docker — containers make Ubuntu/macOS/Windows look the same **inside the image**. **Without an orchestrator**, Docker **moves** complexity to another level:

- binding paths on the local machine to paths inside the container;
- UID/GID and file permissions;
- compose + PostgreSQL + ports;
- pip packages must be installed **inside** the container;
- the debugger must reach the process inside the container.

With **odpm** (orchestrator on top of Docker):

- on the host — Docker, git, and odpm; **one** launch flow on any desktop OS;
- the Odoo stack (Debian image, Python, venv, postgres, compose) **in the container** from one `odpm.json`;
- automatic generation of `docker-compose.yml`, Dockerfile, odoo.conf, volume mapping, debugger setup, and the rest of the “docker layer”.

### 5. “Everyone has their own setup” — team pain

**Without a shared manifest:**

- Python 3.10 on one laptop, 3.12 on another;
- different OCA dependency states;
- different ways to bring up postgres/debugger;
- onboarding = a long checklist with dozens of items.

With **odpm** — split **team** ([`odpm.json`](../reference/odpm-json.md) + lock in git) vs **personal** ([`user_settings.json`](../reference/user-settings.md), per-machine `.env`). The coordinator pins the stack; everyone else reproduces what was declared. See [config split](../reference/config-split.md).

### 6. Three roles — one engine

One codebase, different behavior via [`ODPM_SCENARIO`](../reference/env-dotenv.md):

| Role | Pain without odpm | What odpm gives |
|------|-------------------|-----------------|
| **Developer** | long per-machine setup | [`developer`](../scenarios/developer.md): full dev toolkit, debugger, CLI, VS Code and PyCharm |
| **Server / VM** | separate project wiring | [`server`](../scenarios/server.md): same stack, no dev utilities, postgres on localhost |
| **CI** | separate build scripts | [`ci`](../scenarios/ci.md): baked image with the same rules as the team |

One pipeline; the scenario selects the profile.

### 7. Unpredictable re-setup

**Without odpm** (custom scripts, ansible, “setup.sh”, manual compose):

- unclear what is hand-edited vs regenerated;
- re-setup overwrites `docker-compose.yml`, Dockerfile, or config;
- no dry-run — consequences appear only after you run everything;
- no shared “generated vs source of truth” list.

With **odpm:**

- [`odpm plan`](../reference/cli.md) — see the step set and diff before starting the whole system;
- [generated files](../reference/generated-files.md) catalog;
- compose and runtime config are generated from templates under `.odpm/`;
- one manifest describes stack composition.

### 8. Operational tasks scattered across tools

Beyond “start Odoo”, daily work needs:

- DB restore from archive;
- new DB with language/country/demo;
- admin password reset;
- module install/update (`-i` / `-u`);
- pre-commit in the container;
- module secrets without committing to git.

With **odpm** — one CLI orchestrator around one compose stack ([CLI reference](../reference/cli.md), [secrets](../operations/secrets.md)).

### 9. IDE and debugging

**Without odpm:** you must wire `launch.json` with host/container path mappings by hand, set Pylance `extraPaths`, and deal with PyCharm/pydevd compatibility.

With **odpm:** `debug-profile.json`, automatic VS Code / PyCharm config generation, and automatic install of `debugpy` and `odoo-stubs` in the developer scenario. See [IDE debugging](../operations/vscode-debug.md).

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
| Doodba | higher barrier and a DevOps tilt; less beginner-friendly “one button and go” — that is not their style |
| Odoo.sh | SaaS; not available for self-hosted systems and local developer machines |

**odpm** — Odoo-specific Dev Container manager: declarative manifest + scenario + plan + container contract, no cloud lock-in.

---

## What odpm deliberately does not solve

- **Not a PaaS** — no Odoo.sh-style staging/prod.
- **Not full production hardening** — [`server`](../scenarios/server.md) is a profile; nginx/TLS/backup is on you ([security](../operations/security.md)).
- **Not a substitute for learning Odoo** — framework, ORM, modules still require study.
- **Plugins/hooks** — no goal to clone the full Doodba `custom/` hooks surface.
- **Not byte-identical reproducibility** (like Nix) — **practical** reproducibility via lock + image + manifest.

---

## Next steps

1. [Beginner-friendly guide](beginner-friendly.md) — host install and first run.
2. [Local dev from scratch](local-dev-from-scratch.md) — `odpm --init`, first database.
3. [Team coordinator](../scenarios/team-coordinator.md) — lock, non-interactive, CI.
4. [Developer scenario](../scenarios/developer.md) — debugging and `dev_mode`.

---

## In short

> Odoo development breaks on **infrastructure**, not Python syntax: multi-repo, paths, mixed OS and architectures on the team, Docker, venv, config, IDE, CI. odpm turns that into **one reproducible project contour** from `odpm.json` so the team spends time building modules, not rebuilding the environment.
