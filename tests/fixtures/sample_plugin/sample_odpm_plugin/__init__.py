"""Reference sample plugin for contract tests (odpm extension API 1.0)."""

from __future__ import annotations

from dataclasses import dataclass

from dev_project.extensions import ExtensionHostContext, register_hook_runner, register_prepare_step
from dev_project.extensions.api import EXTENSION_API_VERSION
from dev_project.extensions.reference.mailpit import MAILPIT_SERVICE_NAME, MAILPIT_SERVICE_SPEC
from dev_project.plan import PlanStep
from dev_project.prepare.helpers import make_plan_step
from dev_project.prepare.types import PrepareContext

SAMPLE_PLUGIN_ID = "odpm.sample_plugin"
SAMPLE_HOOK_RUNNER_ID = "odpm.sample_plugin.hooks"
SAMPLE_PREPARE_STEP_ID = "sample_plugin.marker"


@dataclass(frozen=True)
class SamplePrepareStepPlugin:
    id: str = SAMPLE_PREPARE_STEP_ID
    description: str = "Sample extension prepare step (contract fixture)"
    order: int = 950

    def evaluate(self, ctx: PrepareContext) -> PlanStep:
        return make_plan_step(
            self.id,
            self.description,
            "noop",
            False,
            f"sample plugin API {EXTENSION_API_VERSION}",
        )

    def execute(self, ctx: PrepareContext) -> None:
        raise AssertionError("sample plugin execute is not used in contract tests")


class SampleHookRunner:
    name = SAMPLE_HOOK_RUNNER_ID
    phases: list[str]

    def __init__(self) -> None:
        self.phases: list[str] = []

    def run_post_clone(self, ctx: ExtensionHostContext) -> None:
        self.phases.append("post_clone")

    def run_post_prepare(self, ctx: ExtensionHostContext) -> None:
        self.phases.append("post_prepare")

    def run_pre_up(self, ctx: ExtensionHostContext) -> None:
        self.phases.append("pre_up")


class SampleMailpitLocalFragment:
    name = MAILPIT_SERVICE_NAME

    def compose_services(self, ctx: ExtensionHostContext) -> dict:
        return {MAILPIT_SERVICE_NAME: dict(MAILPIT_SERVICE_SPEC)}


def register_sample_plugin() -> None:
    """Register sample plugin components (idempotent for repeated test loads)."""
    from dev_project.extensions.registry import get_hook_runner

    try:
        register_prepare_step(SamplePrepareStepPlugin())
    except ValueError:
        pass
    if get_hook_runner(SAMPLE_HOOK_RUNNER_ID) is None:
        register_hook_runner(SAMPLE_HOOK_RUNNER_ID, SampleHookRunner())
