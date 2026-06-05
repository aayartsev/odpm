import os
import shutil
import tempfile
import unittest
from pathlib import Path
from argparse import Namespace
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.bake_venv import VenvInstallSpec, write_ci_bake_dir
from dev_project.host_start_string_builder import StartStringBuilder
from dev_project.scenario_policy import ScenarioPolicy

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEV_PROJECT_DIR = PROJECT_ROOT / "dev_project"


class ScenarioPolicyTests(unittest.TestCase):
    def test_ci_policy(self):
        policy = ScenarioPolicy.from_scenario(constants.CI_SCENARIO)
        self.assertEqual(policy.odoo_image_attr, "odoo_ci_image_name")
        self.assertFalse(policy.include_odoo_volumes)
        self.assertFalse(policy.include_debugger_port)
        self.assertFalse(policy.include_debugpy)
        self.assertTrue(policy.bind_postgres_localhost)
        self.assertTrue(policy.allow_build_image)
        self.assertTrue(policy.skip_vscode)
        self.assertEqual(policy.entrypoint_rel_path, constants.CI_BAKE_ENTRYPOINT)

    def test_server_policy(self):
        policy = ScenarioPolicy.from_scenario(constants.SERVER_SCENARIO)
        self.assertTrue(policy.include_odoo_volumes)
        self.assertFalse(policy.include_debugger_port)
        self.assertFalse(policy.include_debugpy)
        self.assertTrue(policy.bind_postgres_localhost)
        self.assertFalse(policy.allow_build_image)

    def test_developer_policy(self):
        policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        self.assertTrue(policy.include_debugger_port)
        self.assertTrue(policy.include_debugpy)
        self.assertFalse(policy.bind_postgres_localhost)

    def test_compose_fragments_ci(self):
        policy = ScenarioPolicy.from_scenario(constants.CI_SCENARIO)
        self.assertEqual(policy.build_dev_extra_ports("5678:5678"), "")
        self.assertEqual(policy.build_odoo_volumes_block("\n      - x:y\n"), "")
        self.assertEqual(
            policy.build_postgres_port_map("5432:5432"),
            "127.0.0.1:5432:5432",
        )

    def test_compose_fragments_developer(self):
        policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        self.assertIn("5678:5678", policy.build_dev_extra_ports("5678:5678"))
        self.assertIn("volumes:", policy.build_odoo_volumes_block("\n      - x:y\n"))


class WriteCiBakeDirTests(unittest.TestCase):
    def test_main_and_bootstrap_copied_to_bake(self):
        with tempfile.TemporaryDirectory() as context_dir:
            spec = VenvInstallSpec(
                project_dir="/home/odoo",
                venv_dir="/home/odoo/.venv",
                odoo_requirements_path="/home/odoo/odoo/requirements.txt",
                extra_packages=[],
                python_version="3.12",
            )
            bake_dir = write_ci_bake_dir(
                context_dir, spec, str(DEV_PROJECT_DIR)
            )
            self.assertTrue(os.path.isfile(os.path.join(bake_dir, "main.py")))
            self.assertTrue(
                os.path.isfile(os.path.join(bake_dir, "container_bootstrap.py"))
            )
            with open(os.path.join(bake_dir, "main.py")) as main_file:
                main_source = main_file.read()
            with open(
                DEV_PROJECT_DIR / "inside_docker_app" / "main.py"
            ) as src_file:
                self.assertEqual(main_source, src_file.read())


class StartStringBuilderTests(unittest.TestCase):
    def _make_config(self, scenario: str):
        config = MagicMock()
        config.user_env.odpm_scenario = scenario
        config.arguments = Namespace(
            d=None,
            translate=None,
            pip_install=False,
            start_precommit=False,
            export_po_files=None,
            i=False,
            u=False,
            test=False,
            screencasts=False,
            odoo_bin=[],
        )
        config.dev_mode = False
        config.docker_odoo_dir = "/home/odoo/odoo"
        config.docker_project_dir = "/home/odoo"
        config.docker_inside_app = "/home/odoo/dev_project/inside_docker_app"
        config.docker_venv_dir = "/home/odoo/.venv"
        config.platform_name = "odoo"
        config.odoo_version = "19.0"
        config.init_modules = ""
        config.update_modules = ""
        config.docker_odoo_project_dir_path = "/home/odoo/extra-addons/project"
        config.docker_temp_tests_dir = "/home/odoo/odoo_tests"
        config.requirements_txt = []
        config.config_to_json.return_value = b"{}"
        config.generate_odoo_conf_docker_data = MagicMock()
        return config

    def test_ci_entrypoint_without_debugpy(self):
        config = self._make_config(constants.CI_SCENARIO)
        builder = StartStringBuilder(config)
        self.assertIn("/home/odoo/bake/main.py", config.start_string)
        self.assertNotIn("debugpy", config.start_string)

    def test_developer_entrypoint_with_debugpy(self):
        config = self._make_config(constants.DEVELOPER_SCENARIO)
        builder = StartStringBuilder(config)
        self.assertIn(
            "/home/odoo/dev_project/inside_docker_app/main.py",
            config.start_string,
        )
        self.assertIn("debugpy", config.start_string)


class ComposeTemplateMigrationTests(unittest.TestCase):
    def test_deprecated_words_include_legacy_placeholders(self):
        self.assertIn("{DEBUGGER_PORT_MAP}", constants.DEPRECATED_WORDS)
        self.assertIn("{MAPPED_VOLUMES}", constants.DEPRECATED_WORDS)

    def test_program_template_uses_new_placeholders(self):
        template_path = DEV_PROJECT_DIR / "templates" / "docker-compose.yml"
        content = template_path.read_text()
        self.assertIn("{DEV_EXTRA_PORTS}", content)
        self.assertIn("{ODOO_VOLUMES_BLOCK}", content)
        self.assertNotIn("{DEBUGGER_PORT_MAP}", content)


if __name__ == "__main__":
    unittest.main()
