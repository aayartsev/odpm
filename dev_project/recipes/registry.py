"""Recipe discovery: Python builtins + project .odpm/recipes/*.yaml."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from .. import constants
from ..errors import ConfigError
from ..translations import _
from .builtin.apply_modules_from_diff import ApplyModulesFromDiffRecipe
from .protocol import Recipe
from .yaml_loader import load_recipe_yaml_file
from .yaml_recipe import yaml_recipe_from_raw

_PYTHON_BUILTINS: dict[str, Recipe] = {
    ApplyModulesFromDiffRecipe.name: ApplyModulesFromDiffRecipe(),
}


def project_recipes_dir(project_dir: str) -> Path:
    return Path(project_dir) / constants.PROJECT_SERVICE_DIRECTORY / "recipes"


def _load_project_yaml_recipes(project_dir: str | None) -> dict[str, Recipe]:
    if not project_dir:
        return {}
    recipes_dir = project_recipes_dir(project_dir)
    if not recipes_dir.is_dir():
        return {}
    found: dict[str, Recipe] = {}
    for path in sorted(recipes_dir.glob("*.yaml")) + sorted(recipes_dir.glob("*.yml")):
        raw = load_recipe_yaml_file(path)
        recipe = yaml_recipe_from_raw(raw, source=str(path))
        found[recipe.name] = recipe
    return found


def list_recipes(*, project_dir: str | None = None) -> list[Recipe]:
    """Project YAML overrides Python builtins with the same name."""
    merged: dict[str, Recipe] = dict(_PYTHON_BUILTINS)
    merged.update(_load_project_yaml_recipes(project_dir))
    return [merged[name] for name in sorted(merged)]


def get_recipe(name: str, *, project_dir: str | None = None) -> Recipe:
    merged: dict[str, Recipe] = dict(_PYTHON_BUILTINS)
    merged.update(_load_project_yaml_recipes(project_dir))
    recipe = merged.get(name)
    if recipe is None:
        known = ", ".join(sorted(merged)) or "(none)"
        raise ConfigError(
            _("Unknown recipe {NAME!r}. Known recipes: {KNOWN}.").format(
                NAME=name, KNOWN=known
            )
        )
    return recipe


def format_recipe_list(recipes: Iterable[Recipe]) -> str:
    lines = []
    for recipe in recipes:
        desc = (recipe.description or "").strip()
        if desc:
            lines.append(f"{recipe.name}  —  {desc}")
        else:
            lines.append(recipe.name)
    return "\n".join(lines) + ("\n" if lines else "")
