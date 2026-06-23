# ADR-008: i18n host vs container policy (4.5)

**Status:** accepted (4.5-dev)  
**Date:** 2026-06-22

## Context

odpm 4.3+ translates **host CLI** messages via GNU gettext (`dev_project/i18n/`). Container-side code (`dev_project/inside_docker_app/`) emits technical logs consumed by developers in English tooling (IDE, grep, Odoo tracebacks).

Phase L requires a clear boundary so `check_i18n_catalog.py` and `audit_user_strings.py` scope stays maintainable.

## Decision

### Three string tiers

| Tier | Audience | Mechanism | CI |
|------|----------|-----------|-----|
| **User-facing host** | CLI operator | `_()` / `plan_msg()` + `ru_RU` catalog | `check_i18n_catalog.py` — **0 missing** |
| **Human summaries** | CLI operator (high-level) | `host_summaries.MSG_*` + `_()` at log site | included in catalog check |
| **Maintainer / technical** | Debug, lock drift, git internals | English literals OK | `audit_user_strings.py` inventory (warning only) |
| **Container runtime** | In-container Odoo / checker | **English only** — no gettext in `inside_docker_app/` | excluded from host catalog |

### Container policy

- Do **not** add gettext to `inside_docker_app/` in 4.5.
- `host_summaries.MSG_CONTAINER_LOGS_ENGLISH` informs users that attached container output stays English.

### Plural forms

- Host catalog uses plain `{NAME}` placeholders; `ngettext` is **not required** in 4.5 (no plural-only msgids identified).
- Revisit when a user-facing plural is added.

### `odpm plan` (`plan_msg`)

Plan step `reason` / `description` and plan-level warnings are localized at **plan build time** via `dev_project/plan/l10n.py::plan_msg()` so `format_plan` does not double-translate. `check_i18n_catalog.py` collects both `_('...')` and `plan_msg('...')` call sites.

## Consequences

- `scripts/audit_user_strings.py` skips `inside_docker_app/`.
- `ci.yml` job **i18n** runs `check_i18n_catalog.py` as a required PR gate.
- `en_US` `.po` lists all msgids (msgstr = msgid) for completeness; runtime fallback unchanged.
