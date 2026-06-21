"""Unit tests for HostProjectContext."""

import unittest
from dataclasses import FrozenInstanceError

from dev_project.host.cli.args import OdpmCliArgs
from unittest.mock import MagicMock, patch

from dev_project.host.context import HostProjectContext
from dev_project.scenario_policy import ScenarioPolicy
from dev_project import constants


class HostProjectContextTests(unittest.TestCase):
    def _make_config(self, **argument_overrides):
        config = MagicMock()
        config.project_dir = "/tmp/project"
        config.program_dir = "/opt/odpm"
        config.config_home_dir = "/tmp/project/.odpm"
        config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        config.user_env = MagicMock()
        config.arguments = OdpmCliArgs(
            no_git_update=False,
            update_lock=False,
            **argument_overrides,
        )
        config.user_settings = MagicMock(name="user_settings")
        config.project_settings = MagicMock(name="project_settings")
        config.docker_layout = MagicMock(name="docker_layout")
        config.addon_layout = MagicMock(name="addon_layout")
        return config

    def test_from_config_copies_host_view_fields(self):
        config = self._make_config()
        ctx = HostProjectContext.from_config(config)

        self.assertEqual(ctx.project_dir, "/tmp/project")
        self.assertEqual(ctx.program_dir, "/opt/odpm")
        self.assertEqual(ctx.config_home_dir, "/tmp/project/.odpm")
        self.assertIs(ctx.policy, config.policy)
        self.assertIs(ctx.user_env, config.user_env)
        self.assertIs(ctx.arguments, config.arguments)
        self.assertIs(ctx.user_settings, config.user_settings)
        self.assertIs(ctx.project_settings, config.project_settings)
        self.assertIs(ctx.docker_layout, config.docker_layout)
        self.assertIs(ctx.addon_layout, config.addon_layout)

    def test_cli_flag_properties(self):
        config = self._make_config()
        ctx = HostProjectContext.from_config(
            config,
            arguments=OdpmCliArgs(no_git_update=True, update_lock=True),
        )
        self.assertTrue(ctx.skip_git_update)
        self.assertTrue(ctx.update_lock)

    def test_from_config_uses_explicit_arguments_override(self):
        config = self._make_config()
        args = OdpmCliArgs(no_git_update=True, update_lock=False)
        ctx = HostProjectContext.from_config(config, arguments=args)
        self.assertIs(ctx.arguments, args)
        self.assertTrue(ctx.skip_git_update)
        self.assertFalse(ctx.update_lock)

    def test_config_host_context_property_delegates(self):
        from dev_project.config.config import Config

        config = self._make_config()
        with patch(
            "dev_project.host.context.HostProjectContext.from_config",
            wraps=HostProjectContext.from_config,
        ) as mock_from_config:
            ctx = Config.host_context.fget(config)
        mock_from_config.assert_called_once_with(config)
        self.assertEqual(ctx.project_dir, config.project_dir)

    def test_frozen_context_rejects_attribute_assignment(self):
        ctx = HostProjectContext.from_config(self._make_config())
        with self.assertRaises(FrozenInstanceError):
            ctx.project_dir = "/other"


if __name__ == "__main__":
    unittest.main()
