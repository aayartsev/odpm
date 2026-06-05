import unittest
import warnings

from dev_project import constants
from dev_project.compose_command_render import (
    render_compose_command_block,
    render_odpm_config_env_line,
    yaml_scalar,
)
from dev_project.start_command import StartCommand


class ComposeCommandRenderTests(unittest.TestCase):
    def test_yaml_scalar_quotes_special_characters(self):
        self.assertEqual(yaml_scalar("abc"), "abc")
        self.assertEqual(yaml_scalar(""), '""')
        self.assertEqual(yaml_scalar("has space"), '"has space"')

    def test_render_compose_command_block(self):
        block = render_compose_command_block(
            ["python3", "-m", constants.RUN_ODOO_ENTRYPOINT, "--", "exit", "0"]
        )
        self.assertIn("    command:\n", block)
        self.assertIn("      - python3\n", block)
        self.assertIn(f"      - {constants.RUN_ODOO_ENTRYPOINT}\n", block)

    def test_render_odpm_config_env_line(self):
        line = render_odpm_config_env_line("ODPM_CONFIG_B64", "abc123")
        self.assertIn("- ODPM_CONFIG_B64=abc123\n", line)
        self.assertEqual(render_odpm_config_env_line("ODPM_CONFIG_B64", ""), "")


class StartCommandTests(unittest.TestCase):
    def test_to_compose_service_builds_standard_exec_form(self):
        command = StartCommand(
            kind="standard",
            config_b64="abc123",
            docker_project_dir="/home/odoo",
            odoo_bin=[
                "/home/odoo/odoo/odoo-bin",
                "-c",
                "/home/odoo/odoo.conf",
                "-d",
                "demo",
            ],
        )
        service = command.to_compose_service()
        self.assertEqual(service.working_dir, "/home/odoo")
        self.assertEqual(service.config_b64, "abc123")
        self.assertTrue(service.include_config_env)
        self.assertEqual(
            service.command[:4],
            ["python3", "-m", constants.RUN_ODOO_ENTRYPOINT, "--"],
        )
        self.assertEqual(service.command[-2:], ["-d", "demo"])
        self.assertNotIn("debugpy", service.command)

    def test_to_compose_service_bootstrap_only(self):
        command = StartCommand(
            kind="standard",
            config_b64="abc123",
            docker_project_dir="/home/odoo",
            bootstrap_only=True,
        )
        service = command.to_compose_service()
        self.assertEqual(service.command[-2:], ["exit", "0"])

    def test_to_compose_service_pip_install_exec_form(self):
        command = StartCommand(
            kind="pip_install",
            docker_project_dir="/home/odoo",
            pip_install_script="cd /home/odoo && python3 -m pip install pre-commit",
        )
        service = command.to_compose_service()
        self.assertFalse(service.include_config_env)
        self.assertEqual(
            service.command,
            [
                "/bin/bash",
                "-c",
                "cd /home/odoo && python3 -m pip install pre-commit",
            ],
        )

    def test_to_compose_shell_is_deprecated(self):
        command = StartCommand(kind="pip_install", pip_install_script="echo hi")
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            shell = command.to_compose_shell()
        self.assertTrue(any(issubclass(w.category, DeprecationWarning) for w in caught))
        self.assertEqual(shell, "bash -c 'echo hi'")


if __name__ == "__main__":
    unittest.main()
