"""Contract tests for sample_plugin fixture and extension API 1.1."""

from __future__ import annotations

import unittest

from dev_project.extensions import EXTENSION_API_VERSION, assert_extension_api_compatible
from dev_project.extensions.registry import get_hook_runner, reset_extension_registry_state
from dev_project.prepare.registry import get_prepare_steps
from tests.fixtures.sample_plugin import sample_odpm_plugin


class SamplePluginContractTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_extension_registry_state()
        sample_odpm_plugin.register_sample_plugin()

    def tearDown(self) -> None:
        reset_extension_registry_state()

    def test_extension_api_version_supported(self) -> None:
        assert_extension_api_compatible(EXTENSION_API_VERSION)

    def test_sample_prepare_step_registered(self) -> None:
        step_ids = [step.id for step in get_prepare_steps()]
        self.assertIn(sample_odpm_plugin.SAMPLE_PREPARE_STEP_ID, step_ids)

    def test_sample_hook_runner_registered(self) -> None:
        runner = get_hook_runner(sample_odpm_plugin.SAMPLE_HOOK_RUNNER_ID)
        self.assertIsNotNone(runner)
        assert runner is not None
        self.assertEqual(runner.name, sample_odpm_plugin.SAMPLE_HOOK_RUNNER_ID)


if __name__ == "__main__":
    unittest.main()
