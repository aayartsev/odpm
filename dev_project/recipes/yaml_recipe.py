"""YAML-backed linear recipe adapting to the phased Recipe protocol."""

from __future__ import annotations

from typing import Sequence

from ..errors import ConfigError
from ..translations import _
from .types import OdpmStep, RecipeContext, RecipeParam
from .yaml_loader import (
    materialize_yaml_step,
    recipe_params_from_yaml,
    recipe_steps_from_yaml,
)


class YamlRecipe:
    def __init__(
        self,
        *,
        name: str,
        description: str,
        params: Sequence[RecipeParam],
        step_templates: Sequence[tuple[list[str], bool]],
        source: str,
    ) -> None:
        self.name = name
        self.description = description
        self._params = list(params)
        self._step_templates = [(list(argv), capture) for argv, capture in step_templates]
        self.source = source
        self._index = 0

    def params(self) -> Sequence[RecipeParam]:
        return list(self._params)

    def reset(self, ctx: RecipeContext) -> None:
        self._index = 0

    def next_step(self, ctx: RecipeContext) -> OdpmStep | None:
        if self._index >= len(self._step_templates):
            return None
        argv_template, capture = self._step_templates[self._index]
        self._index += 1
        return materialize_yaml_step(
            argv_template,
            capture=capture,
            params=ctx.params,
            environ=ctx.environ,
        )


def yaml_recipe_from_raw(raw: dict, *, source: str) -> YamlRecipe:
    name = str(raw.get("name") or "").strip()
    if not name:
        raise ConfigError(
            _("Recipe YAML missing name: {PATH}").format(PATH=source)
        )
    description = str(raw.get("description") or "").strip()
    params = recipe_params_from_yaml(raw)
    steps = recipe_steps_from_yaml(raw)
    return YamlRecipe(
        name=name,
        description=description,
        params=params,
        step_templates=steps,
        source=source,
    )
