# ADR-018: Scenario-driven env wizard

## Status

Accepted (4.7).

## Context

First-run `.env` wizard asked for dirs and all ports before `ODPM_SCENARIO`, so CI/server hosts answered irrelevant port/debugger questions. CI builder keys (`ODPM_CI_IMAGE_BUILDER`, Kaniko mode, registry) lived only as manual env docs after ADR-016.

## Decision

1. Interactive order: **scenario → locale → scenario-specific prompts**.
2. Branches:
   - `developer` — backup, projects, all ports, debugger prompts;
   - `server` — backup, projects, odoo+postgres ports, debugger defaults;
   - `ci` — projects only + CI builder prompts; ports/backup use defaults.
3. CI prompts: builder (`docker`|`kaniko`); if kaniko — executor mode (**default `direct`**, warn on `docker-run`), base registry (required), final image push y/n.
4. Keys stay in host `.env` only (not `odpm.json` / `user_settings.json`). Non-interactive bootstrap accepts the same CI keys from process env.

## Consequences

- CI machines get a shorter wizard and write builder/registry into `.env` for ADR-017 resolve wiring.
- Existing developer interactive tests updated for prompt order.
- Depends on ADR-017 dotenv→resolve; enables ADR-019 registry usage.

## References

- [docs/reference/env-dotenv.md](../reference/env-dotenv.md)
- ADR-017 (CI prepare-only policy)
