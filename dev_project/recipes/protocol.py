"""Recipe protocol (phased next_step)."""

from __future__ import annotations

from typing import Protocol, Sequence

from .types import OdpmStep, RecipeContext, RecipeParam


class Recipe(Protocol):
    name: str
    description: str

    def params(self) -> Sequence[RecipeParam]:
        ...

    def reset(self, ctx: RecipeContext) -> None:
        ...

    def next_step(self, ctx: RecipeContext) -> OdpmStep | None:
        ...
