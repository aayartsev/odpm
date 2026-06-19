"""Tests for extension registry and prepare-step entry points."""

from __future__ import annotations

import unittest
from dataclasses import dataclass
from unittest.mock import MagicMock

from dev_project.extensions.registry import (
    get_compose_fragment,
    load_entry_point_prepare_steps,
    plugin_manager,
    register_compose_fragment,
    register_prepare_step,
    reset_extension_registry_state,
)
from dev_project.extensions.context import ExtensionHostContext
from dev_project.extensions.specs import OdpmExtensionSpecs, hookimpl
from dev_project.plan import PlanStep
from dev_project.prepare.helpers import make_plan_step
from dev_project.prepare.registry import BUILTIN_PREPARE_STEPS, get_prepare_steps as all_prepare_steps
from dev_project.prepare.types import PrepareContext


@dataclass(frozen=True)
class _SkipPrepareStepPlugin:
    id: str
    description: str
    order: int = 1000

    def evaluate(self, ctx: PrepareContext) -> PlanStep:
        return make_plan_step(
            self.id,
            self.description,
            "skip",
            False,
            "extension plugin test skip",
        )

    def execute(self, ctx: PrepareContext) -> None:
        raise AssertionError("execute must not run in evaluate-only test")


class _ExampleComposeFragment:
    name = "example"

    def compose_services(self, ctx: ExtensionHostContext) -> dict:
        return {"example": {"image": "example:latest"}}


class ExtensionRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_extension_registry_state()

    def tearDown(self) -> None:
        reset_extension_registry_state()

    def test_register_prepare_step_appended_after_builtin(self):
        before = len(all_prepare_steps())
        register_prepare_step(
            _SkipPrepareStepPlugin(
                id="test.extension.skip",
                description="Test extension prepare step",
                order=50,
            )
        )
        steps = all_prepare_steps()
        self.assertEqual(steps[-1].id, "test.extension.skip")
        self.assertEqual(len(steps), before + 1)

    def test_register_prepare_step_evaluate_is_side_effect_free(self):
        register_prepare_step(
            _SkipPrepareStepPlugin(
                id="test.extension.plan",
                description="Plan-only extension step",
            )
        )
        step = all_prepare_steps()[-1]
        ctx = MagicMock()
        outcome = step.evaluate(ctx)
        self.assertEqual(outcome.id, "test.extension.plan")
        self.assertEqual(outcome.outcome, "skip")

    def test_duplicate_prepare_step_id_raises(self):
        plugin = _SkipPrepareStepPlugin(
            id="test.extension.duplicate",
            description="dup",
        )
        register_prepare_step(plugin)
        with self.assertRaises(ValueError):
            register_prepare_step(plugin)

    def test_register_compose_fragment(self):
        register_compose_fragment("example", _ExampleComposeFragment())
        fragment = get_compose_fragment("example")
        self.assertIsNotNone(fragment)
        assert fragment is not None
        services = fragment.compose_services(
            ExtensionHostContext(
                host=MagicMock(),
                repo_odpm_json="/tmp/odpm.json",
            )
        )
        self.assertIn("example", services)

    def test_get_prepare_steps_requires_builtin_argument(self):
        from dev_project.extensions.registry import get_prepare_steps

        merged = get_prepare_steps(BUILTIN_PREPARE_STEPS)
        self.assertEqual(
            [step.id for step in merged[: len(BUILTIN_PREPARE_STEPS)]],
            [step.id for step in BUILTIN_PREPARE_STEPS],
        )

    def test_pluggy_hookspec_registered(self):
        spec = plugin_manager.hook.odpm_prepare_steps.spec
        self.assertIsNotNone(spec)
        assert spec is not None
        self.assertEqual(spec.name, "odpm_prepare_steps")


class ExtensionEntryPointHookTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_extension_registry_state()

    def tearDown(self) -> None:
        reset_extension_registry_state()

    def test_hookimpl_prepare_step_loaded(self):
        class _EntryPlugin:
            @hookimpl
            def odpm_prepare_steps(self):
                return [
                    _SkipPrepareStepPlugin(
                        id="entrypoint.test.step",
                        description="Entry point step",
                        order=10,
                    )
                ]

        plugin_manager.register(_EntryPlugin(), name="entrypoint-test")
        steps = load_entry_point_prepare_steps()
        self.assertEqual(steps[-1].id, "entrypoint.test.step")


if __name__ == "__main__":
    unittest.main()
