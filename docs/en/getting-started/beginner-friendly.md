# Beginner-friendly guide

> **AI-translated** from Russian. See [Why odpm](why-odpm.md) for the full picture of pain points, team roles, and alternatives. Below is a short on-ramp: what to install and where to start.

## Why odpm exists

**odpm** was created to **lower the very high barrier** to Odoo development. The goal is not “install Odoo one more time”, but to give you a **ready workspace**: open a folder in your editor, write a module, run an update — paths, dependencies, and services are already aligned.

If you are just starting, follow [Local dev from scratch](local-dev-from-scratch.md) with your own repository or your team’s (it must include `odpm.json`).

## “Odoo is installed” ≠ “ready to develop”

On Debian you can install a system package; on Fedora an `.rpm`; you can follow a long wiki. The service **will start** and the login page will open. That creates the illusion that “everything is ready”.

A **developer** needs something else: a **single workspace** where all of this is available at once:

| Need | Why it hurts without odpm |
|------|---------------------------|
| **A directory for your code** | The Odoo package install path is not where your modules live |
| **All environment settings in one logical place** | Settings scattered across systemd, Python venv, compose, env vars |
| **System and Python packages** | Some via apt, some via pip — unclear versions and sources |
| **Odoo configuration file** | `addons_path`, data directory, DB manager — wired by hand |
| **Odoo platform source** | Needed to read core code, debug, and update modules sensibly |
| **Dependency project sources** | OCA, corporate repos — each with its own clone and branch |
| **Consistent addon paths** | One missing path → “module not found” with no clear cause |
| **Your codebase next to dependencies** | Otherwise you edit “foreign” trees or fight IDE paths |

You **can** assemble this manually with packages and scattered guides, but you get repeated manual setup on every Odoo version or machine change — not a **developer tool**.

## Second layer: Docker “so everyone has the same stack”

When a team runs Odoo **in a container** for parity across Ubuntu, macOS, and Windows, the problem **does not shrink** — it **doubles**:

- different paths on disk vs inside the container;
- correct **bind mounts** for platform, project, and each dependency;
- **UID/GID** so files do not break between host and container;
- Odoo `addons_path` must match what the process **inside** the container sees;
- ports, PostgreSQL, and optionally the debugger configured separately.

Typical mistakes: forgotten mount, wrong path, dependency missing from `addons_path`, venv rebuilt in the wrong place. Beginners rarely know **which layer** failed — host, Docker, Odoo, or dependencies.

**odpm is the layer that assembles the whole:** one project directory on disk, stack described in **`odpm.json`**, odpm clones repos, generates `docker-compose`, Odoo config, volume mappings, and **commands** for DB backup, module install/update, admin password, and VS Code debugging.

## What you need on your computer

On the **host** you only need:

- [Docker](https://www.docker.com/products/docker-desktop/) — Docker Desktop on Windows and macOS;
- [git](https://git-scm.com/);
- **odpm** installed — see [installation](../install/README.md);
- for debugging — [Visual Studio Code](https://code.visualstudio.com/).

The Odoo Python project and its venv live **in the container**. Do **not** wrap `odpm` in a host venv — that only adds friction.

## First steps

1. Install odpm for your OS.
2. Follow [Local dev from scratch](local-dev-from-scratch.md) with a repository that already has `odpm.json`.
3. On Windows use the [WSL guide](../install/windows-wsl.md).

On `odpm --init`, the **setup wizard** asks for Odoo version, usage scenario, backup and clone directories. Press Enter on unknown answers for sensible defaults.

## In short

> Packaged Odoo **runs**, but does **not** give you a dev workspace. Platform and addon sources, paths, Python env, config, and Docker parity are separate, heavy work. **odpm** folds that into **one project contour** from `odpm.json` so you start with **your code**, not manual stack assembly.
