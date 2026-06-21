# Scaling and a unified team workflow

> **AI-translated** from Russian.

Context on "why odpm" and pain points of distributed teams: [Why odpm](../getting-started/why-odpm.md).

## Idea

**One tool** — **developer**, **system administrator**, and **continuous integration engineer** — work from **one project description** (`odpm.json` and optionally the version lock file `.odpm/deps.lock.json`). What changes is not "a set of different scripts and Dockerfiles", but only the **run scenario** (`ODPM_SCENARIO`): development on a laptop, service on a server, or a ready image for the build pipeline.

This addresses a typical Odoo team pain point: "works on my machine" for the developer, different paths and versions on the test stand, a third environment variant in automated builds.

## Different computers — same contents inside the container

Teams usually have **different workstations**: Linux, Windows (via WSL), macOS; Intel/AMD and Apple Silicon processors. Without a common layer, problems multiply quickly:

- "installs on Ubuntu, not on macOS" (paths, permissions, shell, dependencies);
- Python wheels and native extensions built for one architecture;
- different PostgreSQL and Python versions "on bare metal";
- separate long instructions for each OS.

**odpm moves the Odoo stack into a container** described in `odpm.json`. On the host remain Docker, git, and odpm. Developer on a laptop, administrator on a VPS, and the build machine get **identical contents** inside the container; only source mounting (from disk or from image) and security policy differ.

| On the user's computer (may differ) | Inside the container (same for everyone) |
|-------------------------------------|------------------------------------------|
| Linux, Windows, macOS | Image based on Debian from odpm template |
| Different CPU architecture | Pinned Python versions, environment policy, entry point |
| Own paths to git clones | Same compose rules and config delivery |

odpm alone does not guarantee "ARM laptop = x86_64 build server" parity: for Apple Silicon machines, multi-arch images or a dedicated server of the same architecture matter. But the **rules of the game** (manifest file, compose, dependency pinning) stay shared.

## Roles and scenarios

| Role | Scenario | What they get |
|------|----------|---------------|
| Developer | `developer` | Sources from disk, debugger, Odoo development mode |
| System administrator | `server` | Same project composition, no debugger, stronger DB isolation |
| Build engineer | `ci` | Image with baked sources and Python environment |

The **`odpm plan`** command helps agree before changes: everyone sees the same preparation steps and differences in generated files.

## Three scenarios — one project composition

What changes is **packaging**, not the list of repositories and pinned revisions:

| | `developer` | `server` | `ci` |
|---|-------------|----------|------|
| Odoo and addon sources | Mounted from host disk | Mounted from disk (e.g. VPS) | Baked into image at build time |
| Python environment | Recreated when lock changes | Same | Pre-built in image |
| Debugger | Yes | No | No |
| Typical location | Laptop | Virtual machine / VPS | Continuous integration machine |

## Deployment scale

**Small setup** (pilot, customer demo, single virtual machine):

- `server` scenario (or `developer` only on the developer machine);
- one `docker compose`: Odoo and PostgreSQL;
- HTTPS via **nginx** or another reverse proxy.

**Medium setup** (team + test stand + automated checks):

- developers on `developer`, stand on `server`, build on `ci`;
- one `odpm.json` in a shared git repository;
- compose check on every change.

**Large setup** (image registry, multiple environments):

```text
odpm --build-image  →  image registry  →  deploy (VM, orchestrator)
```

odpm is a **link in building a reproducible Odoo image**, not a replacement for GitHub Actions, GitLab CI, or orchestration systems. Project description and version pinning live in git.

## What gets unified

| Artifact | Developer | Administrator | Build |
|----------|-------------|---------------|-------|
| `odpm.json` / version lock | edits dependencies | reads | checks strictly |
| `docker-compose.yml` | odpm generates | same | same (in ci without host source mounts) |
| Runtime configuration | passed into container | same | baked into image |

> **One project repository, one `odpm.json`, three scenarios — developer, administrator, and build converge on the same Odoo stack. Scale changes packaging (compose on a virtual machine or image in a registry), not project description rules.**
