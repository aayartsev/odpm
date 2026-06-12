import unittest

from dev_project import constants
from dev_project.compose.command_render import (
    render_compose_command_block,
    render_odpm_config_path_env_line,
    yaml_scalar,
)
from dev_project.compose.start_command import StartCommand


class ComposeCommandRenderTests(unittest.TestCase):
    def test_yaml_scalar_quotes_special_characters(self):
        self.assertEqual(yaml_scalar("abc"), "abc")
        self.assertEqual(yaml_scalar(""), '""')
        self.assertEqual(yaml_scalar("has space"), '"has space"')
        self.assertEqual(yaml_scalar("99999"), '"99999"')
        self.assertEqual(yaml_scalar("true"), '"true"')

    def test_render_compose_command_block_quotes_numeric_argv(self):
        block = render_compose_command_block(
            [
                "python3",
                "-m",
                constants.RUN_ODOO_ENTRYPOINT,
                "--",
                "/home/odoo/odoo/odoo-bin",
                "--limit-time-real",
                "99999",
            ]
        )
        self.assertIn('      - "99999"\n', block)

    def test_render_compose_command_block(self):
        block = render_compose_command_block(
            ["python3", "-m", constants.RUN_ODOO_ENTRYPOINT, "--"]
        )
        self.assertIn("    command:\n", block)
        self.assertIn("      - python3\n", block)
        self.assertIn(f"      - {constants.RUN_ODOO_ENTRYPOINT}\n", block)

    def test_render_odpm_config_path_env_line(self):
        line = render_odpm_config_path_env_line(
            "ODPM_CONFIG_PATH", "/run/odpm/config.json"
        )
        self.assertIn("- ODPM_CONFIG_PATH=/run/odpm/config.json\n", line)
        self.assertEqual(render_odpm_config_path_env_line("ODPM_CONFIG_PATH", ""), "")


class StartCommandTests(unittest.TestCase):
    def test_to_compose_service_builds_standard_exec_form(self):
        command = StartCommand(
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
        self.assertTrue(service.include_runtime_config)
        self.assertEqual(
            service.command[:4],
            ["python3", "-m", constants.RUN_ODOO_ENTRYPOINT, "--"],
        )
        self.assertEqual(service.command[-2:], ["-d", "demo"])
        self.assertNotIn("debugpy", service.command)

    def test_to_compose_service_bootstrap_only_has_empty_odoo_argv(self):
        command = StartCommand(
            docker_project_dir="/home/odoo",
            run_mode=constants.RUN_MODE_BOOTSTRAP_ONLY,
        )
        service = command.to_compose_service()
        self.assertEqual(service.command[-1:], ["--"])

    def test_to_compose_service_pre_commit_uses_exec_form_entrypoint(self):
        project_dir = "/home/odoo/extra-addons/project"
        command = StartCommand(
            kind="pre_commit",
            docker_project_dir="/home/odoo",
            pre_commit_project_dir=project_dir,
        )
        service = command.to_compose_service()

        self.assertEqual(service.working_dir, "/home/odoo")
        self.assertFalse(service.include_runtime_config)
        self.assertEqual(
            service.command,
            [
                "python3",
                "-m",
                constants.RUN_PRE_COMMIT_ENTRYPOINT,
                "--",
                project_dir,
            ],
        )
        self.assertNotIn("/bin/bash", service.command)


if __name__ == "__main__":
    unittest.main()
