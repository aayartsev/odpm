# Plan / dry-run matrix (documentation ↔ CI)

Unit gate for **documented odpm features verifiable without a Docker daemon**. Implemented in [`test_scenario_plan_matrix.py`](test_scenario_plan_matrix.py). Docker `compose validate` / `compose up` remain in [`ci-docker.yml`](../.github/workflows/ci-docker.yml).

## Sources

| Document | Topic |
|----------|--------|
| [`docs/reference/tools-by-scenario.md`](../docs/reference/tools-by-scenario.md) | Scenario applicability |
| [`docs/reference/cli.md`](../docs/reference/cli.md) | Plan flags, manifest CLI |
| [`docs/reference/deps-lock.md`](../docs/reference/deps-lock.md) | Lock source, drift |
| [`docs/reference/database-state.md`](../docs/reference/database-state.md) | `database.drift` |
| [`docs/reference/plugins.md`](../docs/reference/plugins.md) | `compose.fragments`, side-effect-free evaluate |
| [`docs/smoke-4.0-checklist.md`](../docs/smoke-4.0-checklist.md) §2B+ | Plan dry-run expectations |

## Registry A — plan and prepare

| ID | Feature | Test | Plan step / CLI |
|----|---------|------|-----------------|
| A1 | `odpm plan` | `PlanMatrixCoreTests.test_a1_plan_cli_all_scenarios` | in-process CLI, exit 0, all scenarios |
| A2 | `--skip-start` | `PlanMatrixCoreTests.test_a2_skip_start_omits_compose_up` | no `compose.up` |
| A3 | `--no-git-update` | `PlanMatrixCoreTests.test_a3_no_git_update_git_steps` | `git.ensure_present` run, `git.materialize` skip |
| A4 | `--update-lock` | `PlanMatrixCoreTests.test_a4_update_lock_collect_without_compose_up` | `git.lock_collect` update |
| A5 | `--plan-format json` | `PlanMatrixFlagsTests.test_a5_plan_format_json`, `PlanMatrixCliInProcessTests.test_plan_json_all_scenarios` | JSON schema fields |
| A6 | `--plan-format table` | `PlanMatrixFlagsTests.test_a6_plan_format_table` | table header |
| A7 | `--plan-show-diff` | `PlanMatrixFlagsTests.test_a7_plan_show_diff` | `plan.diffs` for `git.lock_collect` / deps.lock |
| A8 | `--plan-strict` | `PlanMatrixFlagsTests.test_a8_plan_strict_*` | exit 1 on required changes (table + JSON); exit 0 when none |
| A9 | `--plan-no-docker` | `PlanMatrixFlagsTests.test_a9_plan_no_docker_warning` | probe warning |
| A10 | `database.drift` | `PlanMatrixCoreTests.test_a10_*` | step present; first-run `last_run` warning |
| A11 | Lock source v1/v2 | `PlanMatrixWarningsTests.test_a11_*` | warnings mention `deps.lock.json` / `locks.git` |
| A12 | locks.git ↔ deps.lock drift | `PlanMatrixWarningsTests.test_a12_locks_drift_warning` | drift warning |
| A13 | `--update-lock` + `--no-git-update` | `PlanMatrixWarningsTests.test_a13_update_lock_with_no_git_update_warning` | conflict warning |
| A13b | secrets `.gitignore` | `PlanMatrixWarningsTests.test_a13_secrets_gitignore_warning` | accidental-commit warning |
| A14 | Secrets materialize | `PlanMatrixCoreTests.test_a14_*` | dev/server vs ci |
| A15 | compose template/generate/service | `PlanMatrixCoreTests.test_a15_*` | compose steps noop after idle sync |
| A16 | Mailpit `compose.fragments` | `PlanMatrixCoreTests.test_a16_*`, `PlanMatrixComposeMarkersTests.test_a16_*` | fragments step + YAML artifact |
| A17 | Evaluate side-effect free | `PlanMatrixCoreTests.test_a17_*` | no runtime config write on plan |
| A18 | Manifest hook plan steps (v2) | `PlanMatrixCoreTests.test_a18_*` | `hooks.pre_up` in plan |
| A18b | Scenario overlay hooks in plan | `PlanMatrixCoreTests.test_a18b_*` | `hooks.post_prepare` only for active scenario |
| A19 | Extension prepare step | `PlanMatrixCoreTests.test_a19_*` | registered prepare step |
| A20 | Scenario overlay → compose fragments | `PlanMatrixComposeMarkersTests.test_scenario_overlay_*` | stale regen on `ODPM_SCENARIO` change |

## Registry B — runtime plan steps

| ID | Feature | Test | developer | server | ci |
|----|---------|------|-----------|--------|-----|
| B1 | `ide.debug_profile` | `test_b1_*` | yes | no | no |
| B2 | `vscode.settings` | `test_b2_*` | yes | yes* | no |
| B3 | `pycharm.settings` | `test_b3_*` | yes (pycharm IDE) | — | no |
| B4 | `ci.build_image` | `test_b4_*` | no | no | yes (+ `--build-image`) |
| B5 | `docker.ports.release` | `test_b5_*` | run** | skip | skip |

\* server: `ScenarioPolicy.skip_ide_config` is false — VS Code settings step still planned.  
\** evaluate-only with `check_system=True`; no Docker exec in unit gate.

## Registry C — scenario behaviour

| ID | Feature | Test |
|----|---------|------|
| C7 | Compose markers | `PlanMatrixComposeMarkersTests.test_c7_*` (developer debug port, server localhost postgres, ci image) |

C1–C6 are covered by A1–A4, A14, B1–B5.

## Registry D — manifest CLI

| ID | Command | Test |
|----|---------|------|
| D1 | `manifest validate` v1 | `test_d1_*` |
| D2 | `manifest validate` v2 | `test_d2_*` |
| D3 | invalid v2 service | `test_d3_*` |
| D4 | `manifest migrate` (dry) | `test_d4_*` |
| D5 | migrate includes `locks` | `test_d5_*` |

## Registry E — Docker only (not in this matrix)

- `docker compose up`, golden-path, `-d -i -u -t`, backup, pre-commit, scaffold exec
- `database ensure-role`, live `database status` with postgres
- `--build-image` exec, full `odpm --skip-start` materialize with network git clone
- `compose.validate` exec (`check_docker_compose` + structural `validate_compose_file`)

## Running

```bash
python3 -m unittest tests.test_scenario_plan_matrix -v
```

Included in default `unittest discover` on every PR ([`ci.yml`](../.github/workflows/ci.yml)).
