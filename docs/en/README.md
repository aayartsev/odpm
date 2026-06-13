# odpm documentation

[![ru](https://img.shields.io/badge/lang-ru-blue.svg)](../README.md)

> **AI-translated** from Russian (`docs/`). Reviewed by maintainers incrementally; report issues on [GitHub](https://github.com/aayartsev/odpm/issues).

**odpm** (Odoo Developer Project Manager) helps developers and administrators **build a unified Odoo workspace**: your code, the platform, dependencies, configuration, and containers — from a single `odpm.json` manifest, without manually wiring paths and settings.

This site covers installation, usage scenarios, parameter reference, and day-to-day operations. The text is practical: what to do in each situation, which files to edit, which commands to run.

If you are choosing odpm for a team or project for the first time, start with [Why odpm: problems it solves](getting-started/why-odpm.md) — for all roles (developer, coordinator, DevOps). New to Odoo? Continue with [Beginner-friendly guide](getting-started/beginner-friendly.md): host setup and first steps.

---

## Getting started

| Article | About |
|--------|--------|
| [Why odpm](getting-started/why-odpm.md) | Pain points; without / with odpm; alternatives; boundaries |
| [Beginner-friendly](getting-started/beginner-friendly.md) | Host install; packaged Odoo vs dev workspace; Docker pitfalls |
| [Local dev from scratch](getting-started/local-dev-from-scratch.md) | Project directory, VS Code, `odpm --init`, first DB and modules |
| [Legacy or inherited project](getting-started/legacy-project.md) | Existing repo, logs, change plan, version lock |

## Installing odpm on your machine

| Article | Platform |
|--------|-----------|
| [Debian / Ubuntu (.deb)](../install/linux-deb.md) | Recommended on Linux |
| [Fedora / RHEL (.rpm)](../install/fedora-rpm.md) | Fedora 41 and newer |
| [macOS](../install/macos-pipx.md) | Install via pipx |
| [Windows (WSL)](../install/windows-wsl.md) | Docker Desktop and Linux subsystem |
| [pip and source checkout](../install/pip-legacy.md) | odpm development, systems without a package |

## Scenarios (`ODPM_SCENARIO`)

| Scenario | Article |
|----------|--------|
| `developer` — development on your computer | [developer](../scenarios/developer.md) |
| `server` — VM or server | [server](../scenarios/server.md) |
| `ci` — image for continuous integration | [ci](../scenarios/ci.md) |
| Team coordinator and version lock | [team-coordinator](../scenarios/team-coordinator.md) |
| Custom Odoo platform repository | [platform-fork](../scenarios/platform-fork.md) |
| One team — different roles and machines | [scaling](../scenarios/scaling.md) |

You always choose the scenario yourself; each has its own default behavior — keep that in mind.

## Reference and tools

| Article | Contents |
|--------|------------|
| [Tools by scenario](../reference/tools-by-scenario.md) | Which commands fit each mode |
| [Config hierarchy](../reference/config-hierarchy.md) | What overrides what: CLI, json, `.env` |
| [odpm.json and user_settings.json](../reference/config-split.md) | Stack vs developer workflow |
| [`.env` variables](../reference/env-dotenv.md) | Ports, directories, scenario, message locale |
| [Git repository links](../reference/git-links.md) | HTTPS, SSH, local `file://` |
| [odpm.json](../reference/odpm-json.md) | Project stack manifest |
| [user_settings.json](../reference/user-settings.md) | Modules, database, git behavior |
| [odoo.conf](../reference/odoo-conf.md) | Project file and in-container config |
| [Command-line options](../reference/cli.md) | Full list |
| [deps.lock.json](../reference/deps-lock.md) | Pinned git dependency revisions |
| [Project directory layout](../reference/project-layout.md) | Directories and files |
| [Generated files](../reference/generated-files.md) | Do not edit by hand |
| [odpm message locale](../reference/locale.md) | `ODPM_LOCALE` variable |

## Operations

| Article | Contents |
|--------|------------|
| [IDE debugging](../operations/vscode-debug.md) | `debugpy_listen` (VS Code / PyCharm DAP) and `pydevd_connect` (PyCharm Debug Server) |
| [Local secrets](../operations/secrets.md) | Module API keys and tokens → `/run/odpm/secrets.json` |
| [Non-interactive mode](../operations/non-interactive.md) | Scripts and build machines |
| [Security](../operations/security.md) | Passwords, reverse proxy, ports |
| [Migrating from 3.0](../operations/migration-3-to-4.md) | No backward compatibility |

## For odpm contributors

Contributor docs live in the GitHub repository: [docs/contributing/](https://github.com/aayartsev/odpm/tree/main/docs/contributing).
