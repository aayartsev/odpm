# ADR-023: Local unit parity (source of truth = Linux CI)

## Status

Accepted (4.7+).

## Context

Contributors and agents run `unittest discover` on macOS (including Apple Silicon), under IDE sandboxes, or without host tools such as `gpg`. Those environments produce failures that do **not** reproduce on GitHub Actions `ubuntu-latest` (Python 3.10 / 3.12), which is the merge gate for the **unit** job.

Without a written policy, local red suites are misread as product regressions (database drift, vscode paths, packaging keyrings) and waste review time. Integration gates are already specified in [ADR-006](adr-006-integration-gate-policy.md); unit **how-to** lives in [tests.md](tests.md) but lacked an explicit “what counts as green” decision.

## Decision

1. **Source of truth for unit** — A unit suite is merge-relevant only when it matches CI: `pip install -e ".[test]"` then `python -m unittest discover -s tests -p 'test_*.py'` on **Linux**, Python **3.10** or **3.12** (see [`.github/workflows/ci.yml`](../../.github/workflows/ci.yml)). Local macOS / sandboxed runs are **smoke for the developer**, not a substitute for the CI **unit** check.
2. **Opt-in integration stays opt-in** — Docker / compose / HTTP / golden-path tests remain behind env flags and scripts documented in [tests.md](tests.md) and [ADR-006](adr-006-integration-gate-policy.md). A plain `discover` with dozens of skips is expected and green for the unit gate.
3. **Documented host quirks are not merge blockers** — Failures caused only by host path canonicalization, missing CLI tools, or IDE sandbox restrictions (listed in [tests.md](tests.md) § Host / architecture notes) do **not** block merging if CI **unit** is green. Fix them in code only when they also fail on Linux CI or when hardening path/`gpg` handling is intentional product work.
4. **Agent / automation runs** — Full local discover should use an unrestricted host environment (no filesystem/network sandbox that blocks docker socket, `git`, `gpg`, or writing under `.vscode`). Prefer a dedicated venv; keep per-invocation wall time reasonable for interactive agents (order of minutes for unit; integration scripts have their own longer budgets).

## Consequences

- Reviewers treat “red on my Mac, green on CI unit” as an environment issue first; see the quirk table in [tests.md](tests.md).
- Cursor rules / personal notes should **point at** this ADR and `tests.md`, not replace them.
- New platform-specific flakes should be added to `tests.md` (and, if policy shifts, amended here).

## References

- [tests.md](tests.md) — commands and quirk table
- [ADR-006](adr-006-integration-gate-policy.md) — integration gate tiers
- [ci.md](ci.md) — workflows and local smoke scripts
