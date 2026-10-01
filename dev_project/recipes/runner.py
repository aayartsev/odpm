"""Execute a phased recipe via odpm subprocess re-exec."""

from __future__ import annotations

import os
import subprocess
from typing import Mapping

from ..errors import ConfigError
from ..logging import get_module_logger
from ..translations import _
from .invoke import (
    child_environ,
    current_recipe_depth,
    full_odpm_argv,
    guard_step_argv,
)
from .protocol import Recipe
from .types import OdpmStep, RecipeContext, StepResult

_logger = get_module_logger(__name__)


def resolve_params(
    recipe: Recipe,
    *,
    cli_values: Mapping[str, str | None],
    environ: Mapping[str, str],
) -> dict[str, str]:
    resolved: dict[str, str] = {}
    for param in recipe.params():
        cli_val = cli_values.get(param.name)
        if cli_val is not None and str(cli_val).strip():
            resolved[param.name] = str(cli_val).strip()
            continue
        if param.env:
            env_val = str(environ.get(param.env) or "").strip()
            if env_val:
                resolved[param.name] = env_val
                continue
        if param.required:
            hint = f" / env {param.env}" if param.env else ""
            raise ConfigError(
                _(
                    "Recipe {RECIPE} requires param {NAME}{HINT}."
                ).format(RECIPE=recipe.name, NAME=param.name, HINT=hint)
            )
    return resolved


def run_recipe(
    recipe: Recipe,
    *,
    project_dir: str,
    program_dir: str,
    params: dict[str, str],
    environ: dict[str, str] | None = None,
    dry_run: bool = False,
    cwd: str | None = None,
) -> int:
    env = dict(environ if environ is not None else os.environ)
    depth = current_recipe_depth(env)
    if depth >= 1:
        raise ConfigError(
            _(
                "Nested 'odpm run' is not allowed "
                "(ODPM_RECIPE_DEPTH={DEPTH}, max nesting 0)."
            ).format(DEPTH=depth)
        )
    child_depth = depth + 1

    ctx = RecipeContext(
        project_dir=project_dir,
        program_dir=program_dir,
        params=params,
        environ=env,
        dry_run=dry_run,
    )
    recipe.reset(ctx)
    work_cwd = cwd or project_dir

    while True:
        step = recipe.next_step(ctx)
        if step is None:
            break
        guard_step_argv(step.argv)
        full_argv = full_odpm_argv(step.argv)
        ctx.planned_argv.append(list(full_argv))

        should_exec = (not dry_run) or step.execute_even_if_dry_run
        if not should_exec:
            ctx.step_results.append(
                StepResult(returncode=0, stdout="", stderr="", skipped=True)
            )
            _logger.info(
                _("dry-run skip: {ARGV}").format(ARGV=" ".join(full_argv))
            )
            continue

        result = _exec_step(
            step,
            full_argv=full_argv,
            cwd=work_cwd,
            environ=child_environ(env, depth=child_depth),
        )
        ctx.step_results.append(result)
        if result.returncode != 0:
            raise ConfigError(
                _("Recipe {RECIPE} step failed (exit {CODE}): {ARGV}").format(
                    RECIPE=recipe.name,
                    CODE=result.returncode,
                    ARGV=" ".join(step.argv),
                ),
                exit_code=result.returncode or 1,
            )

    if dry_run:
        for argv in ctx.planned_argv:
            print(" ".join(argv), flush=True)
    return 0


def _exec_step(
    step: OdpmStep,
    *,
    full_argv: list[str],
    cwd: str,
    environ: dict[str, str],
) -> StepResult:
    _logger.info(_("recipe step: {ARGV}").format(ARGV=" ".join(full_argv)))
    run_kwargs: dict = {
        "cwd": cwd,
        "env": environ,
        "text": True,
    }
    if step.timeout is not None:
        run_kwargs["timeout"] = step.timeout
    if step.capture:
        # Capture stdout only so live logs/progress on stderr remain visible.
        run_kwargs["stdout"] = subprocess.PIPE
        run_kwargs["stderr"] = None
        completed = subprocess.run(full_argv, **run_kwargs)
        return StepResult(
            returncode=completed.returncode,
            stdout=completed.stdout or "",
            stderr="",
        )
    completed = subprocess.run(full_argv, **run_kwargs)
    return StepResult(returncode=completed.returncode, stdout="", stderr="")
