"""Runtime-phase plan steps (after prepare)."""

from __future__ import annotations

from ..host.cli.args import OdpmCliArgs
from ..host.context import HostProjectContext
from ..plan import PlanStep
from ..debugger.ide import ide_includes_pycharm, ide_includes_vscode
from ..plan.compose_preview import vscode_settings_up_to_date
from ..plan.pycharm_preview import (
    pycharm_run_config_description,
    pycharm_run_config_up_to_date,
)
from ..plan.debug_profile_preview import debug_profile_needs_update
from ..plan.compose_runtime import compose_up_would_run, evaluate_compose_up_plan
from ..config import Config
from ..project_env import CreateProjectEnvironment
from .helpers import make_plan_step


def evaluate_runtime_ci_build_image(
    config: Config, args: OdpmCliArgs
) -> PlanStep | None:
    if not args.build_image:
        return None
    if not config.policy.allow_build_image:
        return None
    return make_plan_step(
        "ci.build_image",
        "Build CI Docker image from prepared context",
        "run",
        True,
        "build CI image from prepared context",
    )


def evaluate_runtime_debug_profile(
    config: Config, project_env: CreateProjectEnvironment | None = None
) -> PlanStep | None:
    if not config.policy.include_debugpy:
        return None
    description = "Write .odpm/runtime/debug-profile.json"
    needs_update, reason = debug_profile_needs_update(config, project_env)
    if needs_update:
        return make_plan_step(
            "ide.debug_profile",
            description,
            "run",
            False,
            reason,
        )
    return make_plan_step(
        "ide.debug_profile",
        description,
        "noop",
        False,
        reason,
    )


def evaluate_runtime_vscode_settings(
    config: Config, project_env: CreateProjectEnvironment | None = None
) -> PlanStep | None:
    if config.policy.skip_ide_config:
        return None
    if not ide_includes_vscode(config.user_env.odpm_ide):
        return None
    description = "Update VS Code launch and workspace settings"
    if vscode_settings_up_to_date(config):
        return make_plan_step(
            "vscode.settings",
            description,
            "noop",
            False,
            "VS Code settings already present",
        )
    return make_plan_step(
        "vscode.settings",
        description,
        "run",
        False,
        "refresh VS Code launch and settings",
    )


def evaluate_runtime_pycharm_settings(
    config: Config, project_env: CreateProjectEnvironment | None = None
) -> PlanStep | None:
    if config.policy.skip_ide_config:
        return None
    if not ide_includes_pycharm(config.user_env.odpm_ide):
        return None
    description = pycharm_run_config_description(config)
    if pycharm_run_config_up_to_date(config, project_env):
        return make_plan_step(
            "pycharm.settings",
            description,
            "noop",
            False,
            "PyCharm run configuration already present",
        )
    return make_plan_step(
        "pycharm.settings",
        description,
        "run",
        False,
        description,
    )


def evaluate_runtime_compose_up(
    config: Config, args: OdpmCliArgs, host_ctx: HostProjectContext
) -> PlanStep | None:
    if not compose_up_would_run(args, host_ctx):
        return None
    description = "Run docker compose up"
    reason, _extra_warnings = evaluate_compose_up_plan(config, args)
    return make_plan_step(
        "compose.up",
        description,
        "run",
        True,
        reason,
    )


def build_runtime_plan_steps(
    config: Config,
    args: OdpmCliArgs,
    host_ctx: HostProjectContext,
    project_env: CreateProjectEnvironment | None = None,
) -> tuple[PlanStep, ...]:
    steps: list[PlanStep] = []
    for evaluator in (
        lambda: evaluate_runtime_ci_build_image(config, args),
        lambda: evaluate_runtime_debug_profile(config, project_env),
        lambda: evaluate_runtime_vscode_settings(config, project_env),
        lambda: evaluate_runtime_pycharm_settings(config, project_env),
        lambda: evaluate_runtime_compose_up(config, args, host_ctx),
    ):
        step = evaluator()
        if step is not None:
            steps.append(step)
    return tuple(steps)


def build_runtime_plan_warnings(
    config: Config, args: OdpmCliArgs, host_ctx: HostProjectContext
) -> tuple[str, ...]:
    if not compose_up_would_run(args, host_ctx):
        return ()
    _reason, extra_warnings = evaluate_compose_up_plan(config, args)
    return extra_warnings
