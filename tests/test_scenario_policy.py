import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from argparse import Namespace
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.bake_venv import VenvInstallSpec, write_ci_venv_install_spec
from dev_project.config import Config
from dev_project.project_env import CreateProjectEnvironment
from dev_project.project_env.ci_image import CiImageBuilder
from dev_project.host_start_string_builder import StartStringBuilder
from dev_project.scenario_policy import ScenarioPolicy, is_debugpy_requirement

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEV_PROJECT_DIR = PROJECT_ROOT / "dev_project"


def normalize_as_host_config(
    scenario: str, requirements_txt: list[str], python_version: str = "3.12"
) -> list[str]:
    """Same normalization path as host_config.Config after reading odpm.json."""
    policy = ScenarioPolicy.from_scenario(scenario)
    return policy.normalize_requirements(
        requirements_txt, python_version=python_version
    )


class ScenarioPolicyTests(unittest.TestCase):
    def test_ci_policy(self):
        policy = ScenarioPolicy.from_scenario(constants.CI_SCENARIO)
        self.assertEqual(policy.odoo_image_attr, "odoo_ci_image_name")
        self.assertFalse(policy.include_odoo_volumes)
        self.assertFalse(policy.include_debugger_port)
        self.assertFalse(policy.include_debugpy)
        self.assertFalse(policy.install_debugpy)
        self.assertTrue(policy.bind_postgres_localhost)
        self.assertTrue(policy.allow_build_image)
        self.assertTrue(policy.skip_vscode)
        self.assertEqual(policy.entrypoint_module, constants.DEV_ENTRYPOINT)
        self.assertEqual(policy.venv_mode, constants.VENV_MODE_BAKED)
        self.assertTrue(policy.venv_is_baked())
        self.assertFalse(policy.allows_venv_recreate())
        self.assertTrue(policy.is_ci())
        self.assertFalse(policy.is_developer())

    def test_server_policy(self):
        policy = ScenarioPolicy.from_scenario(constants.SERVER_SCENARIO)
        self.assertTrue(policy.include_odoo_volumes)
        self.assertFalse(policy.include_debugger_port)
        self.assertFalse(policy.include_debugpy)
        self.assertFalse(policy.install_debugpy)
        self.assertTrue(policy.bind_postgres_localhost)
        self.assertFalse(policy.allow_build_image)
        self.assertEqual(policy.venv_mode, constants.VENV_MODE_FRESH)
        self.assertFalse(policy.venv_is_baked())
        self.assertTrue(policy.allows_venv_recreate())
        self.assertFalse(policy.is_ci())
        self.assertFalse(policy.is_developer())

    def test_developer_policy(self):
        policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        self.assertTrue(policy.include_debugger_port)
        self.assertTrue(policy.include_debugpy)
        self.assertTrue(policy.install_debugpy)
        self.assertFalse(policy.bind_postgres_localhost)
        self.assertEqual(policy.venv_mode, constants.VENV_MODE_FRESH)
        self.assertFalse(policy.venv_is_baked())
        self.assertTrue(policy.allows_venv_recreate())
        self.assertFalse(policy.is_ci())
        self.assertTrue(policy.is_developer())

    def test_config_to_json_includes_venv_mode(self):
        config = MagicMock()
        config.user_env.odpm_scenario = constants.SERVER_SCENARIO
        config.policy = ScenarioPolicy.from_scenario(constants.SERVER_SCENARIO)
        config.docker_odoo_dir = "/home/odoo/odoo"
        config.odoo_config_data = {}
        config.docker_path_odoo_conf = "/home/odoo/odoo.conf"
        config.arguments = Namespace()
        config.db_creation_data = {}
        config.db_manager_password = ""
        config.docker_venv_dir = "/home/odoo/.venv"
        config.docker_project_dir = "/home/odoo"
        config.requirements_txt = []
        config.odoo_version = "19.0"
        config.python_version = "3.12"
        config.platform_name = "odoo"
        config.arch = "amd64"
        config.sql_queries = []
        config.update_modules = ""
        config.docker_dirs_with_addons = []
        config.config_dict = {"arch": "amd64", "python_version": "3.12"}
        config.compute_venv_lock_hash.return_value = "abc"

        payload = json.loads(Config.config_to_json(config).decode("utf-8"))
        self.assertEqual(payload["venv_mode"], constants.VENV_MODE_FRESH)
        self.assertEqual(payload["odpm_scenario"], constants.SERVER_SCENARIO)

    def test_policy_invariant_include_implies_install(self):
        for scenario in constants.ODPM_SCENARIO_VALUES:
            policy = ScenarioPolicy.from_scenario(scenario)
            if policy.include_debugpy:
                self.assertTrue(
                    policy.install_debugpy,
                    f"{scenario}: runtime debugpy requires package install",
                )

    def test_is_debugpy_requirement_recognizes_real_pip_specs(self):
        self.assertTrue(is_debugpy_requirement("debugpy==1.8.0"))
        self.assertTrue(is_debugpy_requirement("DEBUGPY>=1.0"))
        self.assertTrue(is_debugpy_requirement("debugpy[test]==1.7.0"))
        self.assertFalse(is_debugpy_requirement("requests==2.31.0"))
        self.assertFalse(is_debugpy_requirement("notdebugpy==1.0"))

    def test_server_strips_debugpy_from_odpm_json_like_list(self):
        # User added debugpy in odpm.json on a server deployment — must be removed.
        normalized = normalize_as_host_config(
            constants.SERVER_SCENARIO,
            ["debugpy==1.8.0", "requests==2.31.0", "pre-commit"],
        )
        self.assertIn("requests==2.31.0", normalized)
        self.assertIn("pre-commit", normalized)
        self.assertFalse(any(is_debugpy_requirement(req) for req in normalized))

    def test_developer_typical_odpm_json_gets_pinned_debugpy(self):
        # Typical developer project: only project tools, no debugpy in odpm.json.
        normalized = normalize_as_host_config(
            constants.DEVELOPER_SCENARIO,
            ["pre-commit", "black"],
            python_version="3.12",
        )
        expected = constants.DEBUGPY.get("3.12", constants.DEFAULT_DEBUGPY)
        self.assertIn("pre-commit", normalized)
        self.assertIn("black", normalized)
        self.assertIn(expected, normalized)
        self.assertEqual(
            sum(1 for req in normalized if is_debugpy_requirement(req)),
            1,
        )

    def test_developer_replaces_user_debugpy_with_pinned_version(self):
        normalized = normalize_as_host_config(
            constants.DEVELOPER_SCENARIO,
            ["debugpy==0.0.1", "requests==2.31.0"],
            python_version="3.12",
        )
        expected = constants.DEBUGPY.get("3.12", constants.DEFAULT_DEBUGPY)
        self.assertIn(expected, normalized)
        self.assertIn("requests==2.31.0", normalized)
        self.assertNotIn("debugpy==0.0.1", normalized)

    def test_ci_venv_spec_excludes_debugpy_after_normalization(self):
        # Simulates CreateProjectEnvironment._build_ci_venv_install_spec input.
        normalized = normalize_as_host_config(
            constants.CI_SCENARIO,
            ["debugpy==1.8.0", "requests==2.31.0"],
        )
        spec = VenvInstallSpec(
            project_dir="/home/odoo",
            venv_dir="/home/odoo/.venv",
            odoo_requirements_path="/home/odoo/odoo/requirements.txt",
            extra_packages=normalized,
            python_version="3.12",
        )
        self.assertIn("requests==2.31.0", spec.extra_packages)
        self.assertFalse(
            any(is_debugpy_requirement(pkg) for pkg in spec.extra_packages)
        )

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


class CiVenvInstallSpecTests(unittest.TestCase):
    def test_build_ci_venv_install_spec_uses_normalized_requirements(self):
        """CI bake reads config.requirements_txt after host_config normalization."""
        config = MagicMock()
        config.requirements_txt = normalize_as_host_config(
            constants.CI_SCENARIO,
            ["debugpy==1.8.0", "requests==2.31.0"],
        )
        config.docker_project_dir = "/home/odoo"
        config.docker_venv_dir = "/home/odoo/.venv"
        config.docker_odoo_dir = "/home/odoo/odoo"
        config.python_version = "3.12"
        config.compute_venv_lock_hash.return_value = "abc123"
        config.config_dict = {}

        spec = CreateProjectEnvironment(config)._build_ci_venv_install_spec()

        self.assertIn("requests==2.31.0", spec.extra_packages)
        self.assertFalse(
            any(is_debugpy_requirement(pkg) for pkg in spec.extra_packages)
        )


class WriteCiVenvInstallSpecTests(unittest.TestCase):
    def test_writes_json_under_ci_dir(self):
        with tempfile.TemporaryDirectory() as context_dir:
            spec = VenvInstallSpec(
                project_dir="/home/odoo",
                venv_dir="/home/odoo/.venv",
                odoo_requirements_path="/home/odoo/odoo/requirements.txt",
                extra_packages=[],
                python_version="3.12",
            )
            config_path = write_ci_venv_install_spec(context_dir, spec)
            self.assertEqual(
                config_path,
                os.path.join(context_dir, constants.CI_VENV_INSTALL_JSON),
            )
            self.assertTrue(os.path.isfile(config_path))
            with open(config_path) as config_file:
                payload = json.load(config_file)
            self.assertEqual(payload["project_dir"], "/home/odoo")
            self.assertFalse(os.path.exists(os.path.join(context_dir, "bake")))

    def test_copy_dev_project_for_ci_places_runtime_package_without_templates(self):
        with tempfile.TemporaryDirectory() as context_dir:
            config = MagicMock()
            config.program_dir = str(PROJECT_ROOT)
            config.docker_project_dir = "/home/odoo"
            config.docker_dev_project_dir = "/home/odoo/dev_project"
            env = MagicMock()
            env.config = config
            CiImageBuilder(env)._copy_dev_project_for_ci(context_dir)

            dest = os.path.join(context_dir, "dev_project")
            self.assertTrue(os.path.isfile(os.path.join(dest, "bake_venv.py")))
            self.assertTrue(
                os.path.isfile(os.path.join(dest, "inside_docker_app", "main.py"))
            )
            self.assertFalse(os.path.isdir(os.path.join(dest, "templates")))
            self.assertFalse(os.path.isdir(os.path.join(dest, "i18n")))
            self.assertFalse(os.path.isdir(os.path.join(dest, "plugins")))
            main_path = os.path.join(dest, "inside_docker_app", "main.py")
            with open(main_path) as main_file:
                main_source = main_file.read()
            with open(
                DEV_PROJECT_DIR / "inside_docker_app" / "main.py"
            ) as src_file:
                self.assertEqual(main_source, src_file.read())


class StartStringBuilderTests(unittest.TestCase):
    def _make_config(self, scenario: str):
        config = MagicMock()
        config.user_env.odpm_scenario = scenario
        config.policy = ScenarioPolicy.from_scenario(scenario)
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
        StartStringBuilder(config).build()
        self.assertIn(
            f"python3 -m {constants.DEV_ENTRYPOINT}",
            config.start_string,
        )
        self.assertNotIn("debugpy", config.start_string)

    def test_server_entrypoint_without_debugpy(self):
        config = self._make_config(constants.SERVER_SCENARIO)
        StartStringBuilder(config).build()
        self.assertIn(
            f"python3 -m {constants.DEV_ENTRYPOINT}",
            config.start_string,
        )
        self.assertNotIn("debugpy", config.start_string)

    def test_developer_entrypoint_with_debugpy(self):
        config = self._make_config(constants.DEVELOPER_SCENARIO)
        StartStringBuilder(config).build()
        self.assertIn(
            f"python3 -m {constants.DEV_ENTRYPOINT}",
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
