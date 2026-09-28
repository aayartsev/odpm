# Beginner-friendly guide

> **AI-translated** from Russian. Arguments for why the project exists, team roles, and alternatives — in [Why odpm](why-odpm.md). Below is a quick on-ramp for beginners: what to install and where to start.

## Why odpm exists

**odpm** was created to **lower the very high barrier** to Odoo development. The goal is not “install Odoo one more time”, but to give you a **ready workspace**: open a folder in your editor, write a module, run an update — paths, dependencies, and services are already aligned.

If you are just starting, follow [Local dev from scratch](local-dev-from-scratch.md), or start with your own repository or your team’s (it must already include `odpm.json`).

## “Odoo is installed” and “ready to develop” are far apart

To simply run Odoo on Debian you can install a system package; on Fedora an `.rpm`; on Windows an `exe` for a given version; or you can follow a long online guide. The service **will start** and the login page will open. It looks like “everything is ready”.

A **developer** needs something else: a **single workspace** where all of this is available at once:

| Need | Why it hurts without odpm |
|------|---------------------------|
| **A directory for your code** | The Odoo package install path is not where your modules live |
| **All environment settings in one logical place** | So every part of the Odoo platform is at hand and manageable: a Python venv for your pip packages, docker-compose, environment variables, and so on |
| **System and Python packages** | Some libraries needed to build Python dependencies go on the host system, some via pip — unclear versions and sources |
| **Odoo configuration file** | `addons_path` and data directory are wired by hand |
| **Odoo platform source** | Needed to read core code, debug, and update modules sensibly |
| **Dependency project sources** | OCA, corporate repos — each with its own clone and branch |
| **Consistent addon paths** | One missing path in the config → “module not found” with no clear cause |
| **Your codebase next to dependencies** | Solid work needs access to “foreign” trees, and that code must be reachable for debugging — IDE path confusion often starts here |

You **can** assemble this manually with packages and scattered guides, but you get repeated manual setup on every Odoo version or machine change — not a **developer tool**.

## Second layer: Docker “so everyone has the same stack”

When a team runs Odoo **in a container** so Linux, macOS, and Windows share one runtime, the problem **does not shrink** — it **doubles**:

- different paths on disk vs inside the container;
- correct **bind mounts** for platform, project, and each dependency;
- **UID/GID** so files do not break between host and container;
- Odoo `addons_path` must match what the process **inside** the container sees;
- network ports, PostgreSQL, and optionally the debugger configured separately;
- sometimes you must install your own pip libraries in the container and still tell teammates about them.

Typical mistakes: forgotten mount, wrong path, dependency missing from `addons_path`, venv rebuilt in the wrong place. Not only beginners but experienced developers often cannot tell **which layer** failed — host, Docker, Odoo, or which dependency.

**odpm is the layer that assembles everything into one whole:** one project directory on disk, stack described in **`odpm.json`**, odpm clones repos, generates `docker-compose`, Odoo config, volume mappings, and **commands** for restoring a database from an archive, module install, admin password change, and IDE debugging.

## What you need on your computer

On the **host** you only need:

- [Docker](https://www.docker.com/products/docker-desktop/) — Docker Desktop on Windows and macOS; on Linux prefer the native Docker service so it runs without an extra virtualization layer;
- [git](https://git-scm.com/);
- **odpm** installed — see [installation](../install/README.md);
- for development and debugging — [Visual Studio Code](https://code.visualstudio.com/).

The Odoo Python project and its venv live **in the container**. Do **not** wrap `odpm` in a host venv — that only adds friction.

## First steps

1. Install odpm for your OS.
2. Follow [Local dev from scratch](local-dev-from-scratch.md) with a repository that already has `odpm.json`.
3. On Windows use the [WSL guide](../install/windows-wsl.md).

On `odpm --init`, the **setup wizard** asks for Odoo version, usage scenario, backup and clone directories. Press Enter on unknown answers for sensible defaults.

## In short

> Packaged Odoo **runs**, but does **not** give you a ready workspace. Platform and addon sources, paths, Python env, config, and Docker parity are separate, heavy work. **odpm** folds that into **one project contour** from `odpm.json` so you start with **your code**, not manual stack assembly.
