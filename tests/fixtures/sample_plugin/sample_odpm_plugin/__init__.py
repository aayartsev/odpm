"""Reference sample plugin for contract tests (odpm extension API 1.1)."""

from __future__ import annotations

from dataclasses import dataclass

from dev_project.extensions import (
    ExtensionHostContext,
    assert_extension_api_compatible,
    register_compose_fragment,
    register_hook_runner,
    register_prepare_step,
)
from dev_project.extensions.api import EXTENSION_API_VERSION
from dev_project.extensions.reference.mailpit import MAILPIT_SERVICE_NAME, MAILPIT_SERVICE_SPEC
from dev_project.extensions.specs import hookimpl
from dev_project.plan import PlanStep
from dev_project.prepare.helpers import make_plan_step
from dev_project.prepare.types import PrepareContext

assert_extension_api_compatible(EXTENSION_API_VERSION, plugin_id="odpm.sample_plugin")

SAMPLE_PLUGIN_ID = "odpm.sample_plugin"
SAMPLE_HOOK_RUNNER_ID = "odpm.sample_plugin.hooks"
SAMPLE_PREPARE_STEP_ID = "sample_plugin.marker"
SAMPLE_PATCH_ENV_KEY = "SAMPLE_PLUGIN_PATCH"


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


class SampleComposePlugin:
    name = SAMPLE_PLUGIN_ID

    def compose_services(self, ctx: ExtensionHostContext) -> dict:
        return {MAILPIT_SERVICE_NAME: dict(MAILPIT_SERVICE_SPEC)}

    def compose_service_patches(self, ctx: ExtensionHostContext) -> dict:
        return {
            "odoo": {
                "environment": {
                    SAMPLE_PATCH_ENV_KEY: EXTENSION_API_VERSION,
                }
            }
        }


class SampleOdpmPrepareEntryPoint:
    @hookimpl
    def odpm_prepare_steps(self):
        return SamplePrepareStepPlugin()


class SampleOdpmHooksEntryPoint:
    @hookimpl
    def odpm_hook_runners(self):
        return SampleHookRunner()


prepare_entry_point = SampleOdpmPrepareEntryPoint()
hooks_entry_point = SampleOdpmHooksEntryPoint()


def register_sample_plugin() -> None:
    """Register sample plugin components (idempotent for repeated test loads)."""
    from dev_project.extensions.registry import get_compose_fragment, get_hook_runner

    try:
        register_prepare_step(SamplePrepareStepPlugin())
    except ValueError:
        pass
    if get_hook_runner(SAMPLE_HOOK_RUNNER_ID) is None:
        register_hook_runner(SAMPLE_HOOK_RUNNER_ID, SampleHookRunner())
    if get_compose_fragment(SAMPLE_PLUGIN_ID) is None:
        register_compose_fragment(SAMPLE_PLUGIN_ID, SampleComposePlugin())
