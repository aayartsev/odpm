[![CI](https://github.com/aayartsev/odpm/actions/workflows/ci.yml/badge.svg?branch=4.0-beta)](https://github.com/aayartsev/odpm/actions/workflows/ci.yml)
[![CI Docker](https://github.com/aayartsev/odpm/actions/workflows/ci-docker.yml/badge.svg?branch=4.0-beta)](https://github.com/aayartsev/odpm/actions/workflows/ci-docker.yml)
[![Release packages](https://github.com/aayartsev/odpm/actions/workflows/release-packages.yml/badge.svg?branch=4.0-beta)](https://github.com/aayartsev/odpm/actions/workflows/release-packages.yml)
[![GitHub release](https://img.shields.io/github/v/release/aayartsev/odpm?include_prereleases&label=release)](https://github.com/aayartsev/odpm/releases)
[![packages](https://img.shields.io/badge/packages-.deb%20%7C%20.rpm-2ea44f?style=flat-square)](https://github.com/aayartsev/odpm/releases)

[![ru](https://img.shields.io/badge/lang-ru-blue.svg)](https://aayartsev.github.io/odpm/)
[![code AI-assisted](https://img.shields.io/badge/code-AI--assisted-6366F1?style=flat-square)](https://github.com/aayartsev/odpm/tree/main/docs/contributing#ai-disclosure)
[![AI-translated docs](https://img.shields.io/badge/docs-AI--translated-8B5CF6?style=flat-square)](https://aayartsev.github.io/odpm/en/)

# odpm (Odoo Developer Project Manager)

> **AI-translated** from [Russian documentation](https://aayartsev.github.io/odpm/). Reviewed by maintainers incrementally; report issues on [GitHub](https://github.com/aayartsev/odpm/issues).

> The hard part of Odoo development shows up first in **infrastructure**, not Python syntax: many git repositories, keeping everything that flows from those repos in sync. Teammates may use different OS (macOS, Windows, Linux) and architectures (x86, arm); then you still need Docker, venv, odoo.conf, IDE, CI, and more layers to watch.

`odpm` builds a **full developer workspace** and **the same Odoo environment** for the whole team — including servers and CI. A single `odpm.json` in the repository is enough: odpm prepares directories, containers, configuration, module paths, and typical database operations.

The project was created to **lower the very high barrier** to Odoo development — including solo developers and small teams without a dedicated infrastructure administrator.

## Problems odpm solves

You **can** install Odoo from a system package (deb, rpm, or even a Windows exe) or a long online guide, and the service **will start**. That is **not enough** for **day-to-day development**.

A developer needs more than “bring the server up” — a **full working environment**:

- a directory where they **write their code** (for example modules for a customer or for their company);
- quick access to **all environment settings** — the whole project context, dependencies, and helper systems in one place;
- clear ways to add **system and Python dependencies** inside an isolated environment;
- an **Odoo config file** with correct addon paths;
- **Odoo platform source** for reading, debugging, and updating modules;
- **sources of all linked projects and dependencies** (OCA, corporate repos, modules on the filesystem);
- consistent **addon paths** and **their own codebase** locations;
- all code paths wired into the **debugger**;
- and a quick, convenient way to do many other day-to-day operations.

Assembling this **systematically** by hand is hard even on one machine. Add **Docker** (meant to solve OS and architecture compatibility so everyone has the same stack) and a second complexity layer appears: what to mount from disk, user permissions, paths inside vs outside the container, config paths matching the real filesystem. That is when “it works for my colleague, my module is not found” usually appears.

`odpm` **takes over this assembly:** one project directory on your machine, one `odpm.json` in the module git repo — automatic cloning, `docker-compose` generation, Odoo configuration, restoring a database from an archive with automatic module install, and a debugger already configured in the editor.

Full article (10 problem layers, program roles, alternatives, boundaries): [Why odpm](getting-started/why-odpm.md).

Short on-ramp for beginners: [Beginner-friendly guide](getting-started/beginner-friendly.md).

## Quick start

You need **Docker**, **git**, and **odpm** on the host (see [installation](../install/README.md)).

```bash
mkdir odoo_demo_project-20 && cd odoo_demo_project-20
odpm --init https://github.com/aayartsev/odoo_demo_project.git --branch 20.0 --odoo-bin --stop-after-init

```

On first run the setup wizard asks about directories and scenario; press Enter for unknown answers to use defaults.

After the environment is prepared:
Enable demo data when the database is created, so the module can install demo records that already appear in the UI:
- open `user_settings.json`
- set `"create_demo": true`

```bash
odpm -d test_db -i first_module
```

Open in the browser: `http://127.0.0.1:8069`.

Step-by-step guide: [Local dev from scratch](getting-started/local-dev-from-scratch.md).

## Installing odpm

**[Installing odpm (all platforms)](../install/README.md)**.

## Usage scenarios

The scenario is set by `ODPM_SCENARIO` in `.env`. Same `odpm.json`; different launch mode (debugging, security, image build).

| Value | Who and why |
|-------|-------------|
| `developer` | Developer on their computer: IDE debugging, nearly unrestricted security profile, default passwords |
| `server` | VM or customer server; strict security profile by default |
| `ci` | Baked image for continuous integration pipeline |

Articles: [developer](../scenarios/developer.md) · [server](../scenarios/server.md) · [ci](../scenarios/ci.md) · [team scaling](../scenarios/scaling.md).

## Full documentation

Published site: **[English](https://aayartsev.github.io/odpm/en/)** (EN) · **[Русский](https://aayartsev.github.io/odpm/)** (RU). Full article list — in the left navigation menu.

| Topic | Link |
|-------|------|
| Legacy or inherited project | [legacy-project.md](getting-started/legacy-project.md) |
| Team coordinator role | [team-coordinator.md](../scenarios/team-coordinator.md) |
| Custom Odoo platform fork | [platform-fork.md](../scenarios/platform-fork.md) |
| Git repository links (git, https, file) | [git-links.md](../reference/git-links.md) |
| All command-line options | [cli.md](../reference/cli.md) |
| PostgreSQL state, drift, legacy adoption | [database-state.md](reference/database-state.md) |
| Module deploy marker (`modules diff`) | [deploy-marker.md](reference/deploy-marker.md) |
| Recipes (`odpm run`) | [recipes.md](reference/recipes.md) |
| `.env`, `odpm.json`, `odoo.conf` | [reference](../reference/config-hierarchy.md) |
| Server security | [security.md](../operations/security.md) |

## For odpm contributors

Contributing, tests, UI translations: [contributing/](https://github.com/aayartsev/odpm/tree/main/docs/contributing).

## Project goals

- **OS independence** and CPU architecture where possible (including Apple Silicon via Docker).
- **Project description via `odpm.json`** — new environments deploy automatically.
- **Developer operations:** DB drop/restore, new DB with language and demo data, admin password change, module install/update, translation export, new module scaffold.
- **One project composition — three launch scenarios:** developer, server admin, and build engineer share one manifest; only packaging differs.
