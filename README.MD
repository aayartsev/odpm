[![CI](https://github.com/aayartsev/odpm/actions/workflows/ci.yml/badge.svg?branch=4.0-beta)](https://github.com/aayartsev/odpm/actions/workflows/ci.yml)
[![CI Docker](https://github.com/aayartsev/odpm/actions/workflows/ci-docker.yml/badge.svg?branch=4.0-beta)](https://github.com/aayartsev/odpm/actions/workflows/ci-docker.yml)
[![Release packages](https://github.com/aayartsev/odpm/actions/workflows/release-packages.yml/badge.svg?branch=4.0-beta)](https://github.com/aayartsev/odpm/actions/workflows/release-packages.yml)
[![GitHub release](https://img.shields.io/github/v/release/aayartsev/odpm?include_prereleases&label=release)](https://github.com/aayartsev/odpm/releases)
[![packages](https://img.shields.io/badge/packages-.deb%20%7C%20.rpm-2ea44f?style=flat-square)](https://github.com/aayartsev/odpm/releases)

[![ru](https://img.shields.io/badge/lang-ru-green.svg)](https://aayartsev.github.io/odpm/)
[![code AI-assisted](https://img.shields.io/badge/code-AI--assisted-6366F1?style=flat-square)](docs/contributing/README.md#ai-disclosure)
[![AI-assisted docs](https://img.shields.io/badge/docs-AI--assisted-8B5CF6?style=flat-square)](https://aayartsev.github.io/odpm/en/)

# odpm (Odoo Developer Project Manager)

> The hard part of Odoo development shows up first in **infrastructure**, not Python syntax: many git repositories, keeping everything that flows from those repos in sync. Teammates may use different OS (macOS, Windows, Linux) and architectures (x86, arm); then you still need Docker, venv, odoo.conf, IDE, CI, and more layers to watch.

`odpm` builds a **full developer workspace** and **the same Odoo environment** for the whole team — including servers and CI. A single `odpm.json` in the repository is enough: odpm prepares directories, containers, configuration, module paths, and typical database operations.

The project was created to **lower the very high barrier** to Odoo development — including solo developers and small teams without a dedicated infrastructure administrator.

## Problems odpm solves

You **can** install Odoo from a system package (deb, rpm, or even a Windows exe) or a long online guide, and the service **will start**. That is **not enough** for **day-to-day development**.

A developer needs more than “the server is up” — a **connected whole**:

- a directory where they **write their code** (for example modules for a customer or for their company);
- quick access to **all environment settings** — the whole project context, dependencies, and helper systems in one place;
- clear ways to add **system and Python dependencies** inside an isolated environment;
- an **Odoo config file** with correct addon paths;
- **Odoo platform source** for reading, debugging, and updating modules;
- **sources of all linked projects and dependencies** (OCA, corporate repos, modules on the filesystem);
- consistent **addon paths** and **their own codebase** locations;
- all code paths wired into the **debugger**.

Assembling this **systematically** by hand is hard even on one machine. Add **Docker** (meant to solve OS and architecture compatibility so everyone has the same stack) and a second complexity layer appears: what to mount from disk, user permissions, paths inside vs outside the container, config paths matching the real filesystem. That is when “it works for my colleague, my module is not found” usually appears.

`odpm` **takes over this assembly:** one project directory on your machine, one `odpm.json` in the module git repo — automatic cloning, `docker-compose` generation, Odoo configuration, restoring a database from an archive with automatic module install, and a debugger already configured in the editor.

Full article (10 problem layers, program roles, alternatives, boundaries): [Why odpm](docs/getting-started/why-odpm.md).

Short on-ramp for beginners: [Beginner-friendly guide](docs/getting-started/beginner-friendly.md).

## Quick start

You need **Docker**, **git**, and **odpm** on the host (see [installation](docs/install/README.md)).

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

Step-by-step guide: [Local dev from scratch](docs/getting-started/local-dev-from-scratch.md).

## Installing odpm

Platform overview: **[Installing odpm (all platforms)](docs/install/README.md)**.

## Usage scenarios

The scenario is set by `ODPM_SCENARIO` in `.env`. Same `odpm.json`; different launch mode (debugging, security, image build).

| Value | Who and why |
|-------|-------------|
| `developer` | Developer on their computer: IDE debugging, nearly unrestricted security profile, default passwords |
| `server` | VM or customer server; strict security profile by default |
| `ci` | Baked image for continuous integration pipeline |

Articles: [developer](docs/scenarios/developer.md) · [server](docs/scenarios/server.md) · [ci](docs/scenarios/ci.md) · [team scaling](docs/scenarios/scaling.md).

## Full documentation

Published site: **[https://aayartsev.github.io/odpm/](https://aayartsev.github.io/odpm/)** (RU) · **[English](https://aayartsev.github.io/odpm/en/)** (EN). Table of contents in the repository: **[docs/README.md](docs/README.md)**.

| Topic | Link |
|-------|------|
| Legacy or inherited project | [legacy-project.md](docs/getting-started/legacy-project.md) |
| Team coordinator role | [team-coordinator.md](docs/scenarios/team-coordinator.md) |
| Custom Odoo platform fork | [platform-fork.md](docs/scenarios/platform-fork.md) |
| Git repository links (git, https, file) | [git-links.md](docs/reference/git-links.md) |
| All command-line options | [cli.md](docs/reference/cli.md) |
| `.env`, `odpm.json`, `odoo.conf` | [reference](docs/reference/) |
| Server security | [security.md](docs/operations/security.md) |

## For odpm contributors

Contributing, tests, UI translations: [docs/contributing/README.md](docs/contributing/README.md).

## Project goals

- **OS independence** and CPU architecture where possible (including Apple Silicon via Docker).
- **Project description via `odpm.json`** — new environments deploy automatically.
- **Developer operations:** DB drop/restore, new DB with language and demo data, admin password change, module install/update, translation export, new module scaffold.
- **One project composition — three launch scenarios:** developer, server admin, and build engineer share one manifest; only packaging differs.
