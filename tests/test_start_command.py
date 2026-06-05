import unittest

from dev_project import constants
from dev_project.start_command import StartCommand


class StartCommandTests(unittest.TestCase):
    def test_to_compose_shell_builds_standard_pipeline(self):
        command = StartCommand(
            kind="standard",
            entrypoint=["python3", "-m", constants.DEV_ENTRYPOINT],
            config_b64="abc123",
            docker_project_dir="/home/odoo",
            docker_venv_dir="/home/odoo/.venv",
            debugpy=True,
            odoo_bin=[
                "/home/odoo/odoo/odoo-bin",
                "-c",
                "/home/odoo/odoo.conf",
                "-d",
                "demo",
            ],
        )
        shell = command.to_compose_shell()
        self.assertTrue(shell.startswith("bash -c '"))
        self.assertIn(f"python3 -m {constants.DEV_ENTRYPOINT}", shell)
        self.assertIn("--config-base64-data abc123", shell)
        self.assertIn("debugpy", shell)
        self.assertIn("-d demo", shell)

    def test_to_compose_shell_supports_pip_install_variant(self):
        command = StartCommand(
            kind="pip_install",
            pip_install_script="cd /home/odoo && python3 -m pip install pre-commit",
        )
        self.assertEqual(
            command.to_compose_shell(),
            "bash -c 'cd /home/odoo && python3 -m pip install pre-commit'",
        )


if __name__ == "__main__":
    unittest.main()
