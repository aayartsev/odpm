"""Tests for project-local extension plugin loading."""

from __future__ import annotations

import tempfile
import textwrap
import unittest
from pathlib import Path
from unittest.mock import patch

from dev_project.errors import ConfigError
from dev_project.extensions.local import (
    load_project_local_plugins,
    reset_local_plugins_state,
)
from dev_project.extensions.registry import reset_extension_registry_state
from dev_project.prepare.registry import get_prepare_steps


class LocalPluginLoaderTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_extension_registry_state()
        reset_local_plugins_state()

    def tearDown(self) -> None:
        reset_extension_registry_state()
        reset_local_plugins_state()

    def test_loads_plugin_module_from_odpm_plugins_dir(self) -> None:
        plugin_source = textwrap.dedent(
            '''
            from dev_project.extensions import register_prepare_step
            from dev_project.plan import PlanStep
            from dev_project.prepare.helpers import make_plan_step
            from dev_project.prepare.types import PrepareContext

            class _LocalMarkerPlugin:
                id = "local.marker"
                description = "Local plugin marker"
                order = 900

                def evaluate(self, ctx: PrepareContext) -> PlanStep:
                    return make_plan_step(self.id, self.description, "noop", False, "local")

                def execute(self, ctx: PrepareContext) -> None:
                    raise AssertionError("not executed in test")

            register_prepare_step(_LocalMarkerPlugin())
            '''
        )
        with tempfile.TemporaryDirectory() as project_dir:
            plugins_dir = Path(project_dir) / ".odpm" / "plugins"
            plugins_dir.mkdir(parents=True)
            (plugins_dir / "marker.py").write_text(plugin_source, encoding="utf-8")
            load_project_local_plugins(project_dir)
            step_ids = [step.id for step in get_prepare_steps()]
            self.assertIn("local.marker", step_ids)

    def test_rejects_path_traversal_module_name(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir:
            with self.assertRaises(ConfigError):
                load_project_local_plugins(project_dir, allow_list=("../escape",))

    def test_allow_list_skips_missing_modules(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir:
            with patch("dev_project.extensions.local._logger") as mock_logger:
                load_project_local_plugins(project_dir, allow_list=("missing",))
            mock_logger.warning.assert_called()


if __name__ == "__main__":
    unittest.main()
