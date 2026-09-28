"""Host CLI handlers for odpm run."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from ..errors import ConfigError
from ..logging import get_module_logger
from ..translations import _
from .registry import format_recipe_list, get_recipe, list_recipes
from .runner import resolve_params, run_recipe

if TYPE_CHECKING:
    from ..config import Config
    from ..host.cli.args import OdpmCliArgs

_logger = get_module_logger(__name__)


def run_recipes_command(cli_args: OdpmCliArgs, config: Config | None) -> int:
    project_dir = ""
    program_dir = ""
    if config is not None:
        project_dir = str(getattr(config, "project_dir", "") or "")
        program_dir = str(getattr(config, "program_dir", "") or "")

    if cli_args.run_list:
        try:
            recipes = list_recipes(project_dir=project_dir or None)
        except ConfigError:
            recipes = list_recipes(project_dir=None)
            _logger.warning(
                _("Could not load project recipes; listing builtins only.")
            )
        text = format_recipe_list(recipes)
        print(text, end="", flush=True)
        return 0

    recipe_name = (cli_args.run_recipe or "").strip()
    if not recipe_name:
        raise ConfigError(
            _('Recipe name required: use "odpm run RECIPE" or "odpm run --list".')
        )
    if not project_dir:
        raise ConfigError(_("Project directory is not set."))

    recipe = get_recipe(recipe_name, project_dir=project_dir)
    environ = dict(os.environ)
    cli_values = {
        "database": cli_args.d,
        "diff_base": cli_args.run_diff_base,
    }
    params = resolve_params(recipe, cli_values=cli_values, environ=environ)
    return run_recipe(
        recipe,
        project_dir=project_dir,
        program_dir=program_dir,
        params=params,
        environ=environ,
        dry_run=bool(cli_args.run_dry_run),
        cwd=project_dir,
    )
