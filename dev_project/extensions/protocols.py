"""Extension plugin protocols."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from .context import ExtensionHostContext

if TYPE_CHECKING:
    from ..plan import PlanStep
    from ..prepare.types import PrepareContext, PrepareStepDef


@runtime_checkable
class PrepareStepPlugin(Protocol):
    """Prepare-step plugin exposed via registry or entry points."""

    id: str
    description: str
    order: int

    def evaluate(self, ctx: PrepareContext) -> PlanStep: ...

    def execute(self, ctx: PrepareContext) -> None: ...


@runtime_checkable
class ComposeFragmentPlugin(Protocol):
    """Compose service fragment provider (compose-fragments epic)."""

    name: str

    def compose_services(self, ctx: ExtensionHostContext) -> dict[str, Any]: ...


@runtime_checkable
class HookRunner(Protocol):
    """Manifest hook runner (hooks epic)."""

    def run_post_prepare(self, ctx: ExtensionHostContext) -> None: ...

    def run_pre_up(self, ctx: ExtensionHostContext) -> None: ...


if TYPE_CHECKING:
    PrepareStepSource = PrepareStepPlugin | PrepareStepDef | Sequence[Any]
else:
    PrepareStepSource = Any

PrepareStepFactory = Callable[[], PrepareStepSource]
