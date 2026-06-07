import json
import os
import tempfile
import unittest
from dev_project.host.cli.args import OdpmCliArgs
from pathlib import Path
from unittest.mock import MagicMock

from dev_project import constants, translations
from dev_project.project_env import CreateProjectEnvironment
from dev_project.project_env.services import CiImageBuildService
from dev_project.project_dir_manager import ProjectDirManager
from dev_project.scenario_policy import ScenarioPolicy


class ProjectDockerignoreTests(unittest.TestCase):
    def _program_dir(self) -> str:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _make_manager(self, project_dir: str) -> ProjectDirManager:
        os.makedirs(
            os.path.join(project_dir, constants.PROJECT_SERVICE_DIRECTORY),
            exist_ok=True,
        )
        return ProjectDirManager(
            project_dir,
            OdpmCliArgs(),
            self._program_dir(),
        )

    def test_rebuild_dockerignore_template_copies_program_template(self):
        with tempfile.TemporaryDirectory() as project_dir:
            manager = self._make_manager(project_dir)
            manager.rebuild_dockerignore_template()
            project_template = Path(project_dir) / constants.PROJECT_DOCKERIGNORE_TEMPLATE_FILE_RELATIVE_PATH
            self.assertTrue(project_template.is_file())
            self.assertIn(
                translations.get_translation(translations.MESSAGE_FOR_TEMPLATES),
                project_template.read_text(encoding="utf-8"),
            )

    def test_generate_dockerignore_writes_managed_file(self):
        with tempfile.TemporaryDirectory() as project_dir:
            manager = self._make_manager(project_dir)
            manager.rebuild_dockerignore_template()

            config = MagicMock()
            config.project_dir = project_dir
            config.project_dockerignore_template_path = os.path.join(
                project_dir,
                constants.PROJECT_DOCKERIGNORE_TEMPLATE_FILE_RELATIVE_PATH,
            )
            env = CreateProjectEnvironment(config)
            env.templates.generate_dockerignore()

            dockerignore = Path(project_dir) / constants.DOCKERIGNORE
            self.assertTrue(dockerignore.is_file())
            content = dockerignore.read_text(encoding="utf-8")
            self.assertIn(
                translations.get_translation(translations.DO_NOT_CHANGE_FILE),
                content,
            )
            self.assertIn("**/.git", content)
            self.assertIn(".venv", content)
            self.assertIn(".odpm/ci-build-context", content)

    def test_generate_dockerignore_uses_custom_project_template(self):
        with tempfile.TemporaryDirectory() as project_dir:
            manager = self._make_manager(project_dir)
            manager.rebuild_dockerignore_template()
            project_template = Path(project_dir) / constants.PROJECT_DOCKERIGNORE_TEMPLATE_FILE_RELATIVE_PATH
            project_template.write_text(
                project_template.read_text(encoding="utf-8")
                + "custom-exclusion/\n",
                encoding="utf-8",
            )

            config = MagicMock()
            config.project_dir = project_dir
            config.project_dockerignore_template_path = str(project_template)
            env = CreateProjectEnvironment(config)
            env.templates.generate_dockerignore()

            content = (Path(project_dir) / constants.DOCKERIGNORE).read_text(
                encoding="utf-8"
            )
            self.assertIn("custom-exclusion/", content)

    def test_read_ci_dockerignore_template_reads_program_template(self):
        program_dir = self._program_dir()
        config = MagicMock()
        config.program_dir = program_dir
        env = CreateProjectEnvironment(config)
        content = CiImageBuildService(env).read_ci_dockerignore_template()
        self.assertIn("**/.git", content)
        self.assertIn("dev_project/templates/**", content)
        self.assertIn("dev_project/i18n/**", content)
        self.assertNotIn(".venv", content)
        self.assertNotIn(".odpm/ci-build-context", content)

    def test_prepare_ci_build_context_writes_program_dockerignore(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = MagicMock()
            config.program_dir = self._program_dir()
            config.project_dir = project_dir
            config.ci_build_context_dir = os.path.join(
                project_dir, constants.CI_BUILD_CONTEXT_DIR
            )
            config.odoo_config_data = {"options": {"admin_passwd": "admin"}}
            config.docker_project_dir = "/home/odoo"
            config.docker_venv_dir = "/home/odoo/.venv"
            config.docker_dev_project_dir = "/home/odoo/dev_project"
            config.docker_backups_dir = "/home/odoo/backups"
            config.docker_temp_tests_dir = "/tmp/odoo_tests"
            config.docker_odoo_dir = "/home/odoo/odoo"
            config.docker_extra_addons = "/home/odoo/extra-addons"
            config.docker_path_odoo_conf = "/home/odoo/odoo.conf"
            config.compute_venv_lock_hash.return_value = "abc"
            config.python_version = "3.12"
            config.requirements_txt = []
            config.arch = "amd64"
            config.odoo_version = "19.0"
            config.platform_name = "odoo"
            config.container_run_mode = constants.RUN_MODE_ODOO
            config.db_manager_password = ""
            config.db_creation_data = dict(constants.DEFAULT_DB_CREATION_DATA)
            config.arguments = OdpmCliArgs()
            config.sql_queries = []
            config.update_modules = ""
            config.docker_dirs_with_addons = []
            config.user_env = MagicMock(odpm_scenario=constants.CI_SCENARIO)
            config.policy = ScenarioPolicy.from_scenario(constants.CI_SCENARIO)

            env = CreateProjectEnvironment(config)
            env.mapped_folders = []
            CiImageBuildService(env).prepare_ci_build_context()

            dockerignore = Path(config.ci_build_context_dir) / constants.DOCKERIGNORE
            self.assertTrue(dockerignore.is_file())
            content = dockerignore.read_text(encoding="utf-8")
            self.assertIn("**/.git", content)
            self.assertNotIn(".venv", content)

            runtime_config = (
                Path(config.ci_build_context_dir)
                / constants.CI_RUNTIME_CONFIG_CONTEXT_REL_PATH
            )
            self.assertTrue(runtime_config.is_file())
            payload = json.loads(runtime_config.read_text(encoding="utf-8"))
            self.assertEqual(payload["odpm_scenario"], constants.CI_SCENARIO)
            self.assertEqual(payload["venv_mode"], constants.VENV_MODE_BAKED)

            dev_project_dest = Path(config.ci_build_context_dir) / "dev_project"
            self.assertTrue((dev_project_dest / "bake_venv.py").is_file())
            self.assertTrue(
                (dev_project_dest / "inside_docker_app" / "run_odoo.py").is_file()
            )
            self.assertFalse((dev_project_dest / "templates").exists())
            self.assertFalse((dev_project_dest / "i18n").exists())
            self.assertTrue(
                (Path(config.ci_build_context_dir) / constants.CI_VENV_INSTALL_JSON).is_file()
            )


if __name__ == "__main__":
    unittest.main()
