import json
import os
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.config import Config, compute_venv_lock_hash, config_to_json
from dev_project.container_config import CONTAINER_CONFIG_SCHEMA_VERSION
from dev_project.config.bootstrap import load_project_settings, load_user_settings
from dev_project.config.loader import ConfigLoader
from dev_project.config.paths import ConfigPaths
from dev_project.config.state import DockerLayoutState, ProjectSettingsState, UserSettingsState
from dev_project.errors import ConfigError, PipelineError
from dev_project.scenario_policy import ScenarioPolicy
from dev_project.dependency_resolver import NestedOdpmFragment


class ConfigLoaderTests(unittest.TestCase):
    def test_beautify_module_list_from_comma_string(self):
        config = MagicMock()
        loader = ConfigLoader(config)
        self.assertEqual(
            loader.beautify_module_list(" sale , purchase "),
            "sale,purchase",
        )

    def test_beautify_module_list_empty_returns_default(self):
        config = MagicMock()
        loader = ConfigLoader(config)
        self.assertEqual(
            loader.beautify_module_list(None),
            constants.DEFAULT_LIST_OF_MODULES,
        )

    def test_check_for_config_renames_legacy_config_json(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = MagicMock()
            config.project_dir = project_dir
            config.config_json_content = {}
            config.config_json_path = ""
            config.config_deprecated_json_path = ""

            legacy_path = os.path.join(project_dir, constants.CONFIG_FILE_NAME)
            Path(legacy_path).write_text('{"init_modules": []}', encoding="utf-8")

            ConfigLoader(config).check_for_config()

            self.assertFalse(os.path.exists(legacy_path))
            deprecated_path = os.path.join(
                project_dir, f"deprecated_{constants.CONFIG_FILE_NAME}"
            )
            self.assertTrue(os.path.exists(deprecated_path))
            self.assertEqual(config.config_json_content, {"init_modules": []})


class ConfigPathsTests(unittest.TestCase):
    def test_get_odoo_ci_image_name_uses_image_tag_when_set(self):
        config = MagicMock()
        config.arguments = Namespace(image_tag=" custom:tag ")
        config.odoo_version = "19.0"
        config.platform_name = "odoo"
        self.assertEqual(
            ConfigPaths(config).get_odoo_ci_image_name(),
            "custom:tag",
        )

    def test_get_odoo_ci_image_name_default_pattern(self):
        config = MagicMock()
        config.arguments = Namespace()
        config.odoo_version = "19.0"
        config.platform_name = "odoo"
        self.assertEqual(
            ConfigPaths(config).get_odoo_ci_image_name(),
            "odoo-19-0-ci:latest",
        )

    def test_get_postgres_data_local_storage_path_creates_directory(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = MagicMock()
            config.pd_manager = MagicMock(project_path=project_dir)
            path = ConfigPaths(config).get_postgres_data_local_storage_path()
            self.assertTrue(os.path.isdir(path))

    def test_apply_symlink_sources_includes_repo_odpm_json_once(self):
        config = MagicMock()
        config.user_env = MagicMock(backups="/tmp/backups")
        config.odoo_src_dir = "/tmp/odoo"
        config.developing_project_dir_path = "/tmp/dev"
        config.repo_odpm_json = "/tmp/dev/odpm.json"
        config.create_module_links = False
        ConfigPaths(config).apply_symlink_sources()
        self.assertEqual(config.list_for_symlinks.count("/tmp/dev/odpm.json"), 1)

    def test_apply_symlink_sources_no_duplicate_when_create_module_links_true(self):
        config = MagicMock()
        config.user_env = MagicMock(backups="/tmp/backups")
        config.odoo_src_dir = "/tmp/odoo"
        config.developing_project_dir_path = "/tmp/dev"
        config.repo_odpm_json = "/tmp/dev/odpm.json"
        config.create_module_links = True
        ConfigPaths(config).apply_symlink_sources()
        self.assertEqual(config.list_for_symlinks.count("/tmp/dev/odpm.json"), 1)
        self.assertEqual(len(config.list_for_symlinks), 4)

    def test_apply_docker_layout_developer_uses_host_identity(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = MagicMock()
            config.project_dir = project_dir
            config.platform_name = constants.PLATFORM_NAME
            config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
            runtime_user = config.policy.runtime_unix_user()

            ConfigPaths(config).apply_docker_layout()

            self.assertEqual(config.docker_project_dir, f"/home/{runtime_user}")
            expected_home = os.path.join(
                project_dir, "data/odoo", f"home/{runtime_user}"
            )
            self.assertEqual(config.dir_for_odoo_container_home, expected_home)
            self.assertTrue(os.path.isdir(os.path.join(expected_home, ".cache")))
            self.assertTrue(os.path.isdir(os.path.join(expected_home, ".local")))

    def test_apply_docker_layout_ci_uses_container_identity(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = MagicMock()
            config.project_dir = project_dir
            config.platform_name = constants.PLATFORM_NAME
            config.policy = ScenarioPolicy.from_scenario(constants.CI_SCENARIO)

            ConfigPaths(config).apply_docker_layout()

            self.assertEqual(config.docker_project_dir, "/home/odoo")
            expected_home = os.path.join(project_dir, "data/odoo", "home/odoo")
            self.assertEqual(config.dir_for_odoo_container_home, expected_home)
            self.assertTrue(os.path.isdir(os.path.join(expected_home, ".cache")))


class ConfigLoaderExtraTests(unittest.TestCase):
    def test_get_developing_project_link_from_legacy_config_json(self):
        config = MagicMock()
        config.config_json_content = {
            "developing_project": "https://github.com/acme/demo.git"
        }
        config.pd_manager = MagicMock(init=".", project_path="/tmp/project")
        link = ConfigLoader(config).get_developing_project_link()
        self.assertEqual(link, "https://github.com/acme/demo.git")

    def test_get_developing_project_link_wraps_relative_init_path(self):
        config = MagicMock()
        config.config_json_content = {}
        config.pd_manager = MagicMock(init="my_repo", project_path="/tmp/project")
        link = ConfigLoader(config).get_developing_project_link()
        self.assertEqual(link, "file:///tmp/project/my_repo")

    def test_check_file_for_deprecated_words_renames_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "docker-compose.yml")
            with open(path, "w", encoding="utf-8") as writer:
                writer.write("services:\n  {DEBUGGER_PORT_MAP}:\n")

            config = MagicMock()
            ConfigLoader(config).check_file_for_deprecated_words(path)

            self.assertFalse(os.path.exists(path))
            self.assertTrue(
                os.path.exists(os.path.join(tmp_dir, "deprecated_docker-compose.yml"))
            )


class ConfigPayloadTests(unittest.TestCase):
    def _base_config_dict(self) -> dict:
        return {
            "python_version": "3.12",
            "distro_name": "debian",
            "distro_version": "12",
            "postgres_version": "16",
            "odoo_version": "19.0",
            "arch": "amd64",
        }

    def _apply_lock_hash_fields(self, config: MagicMock, base_dict: dict) -> None:
        for key, value in base_dict.items():
            setattr(config, key, value)

    def test_compute_venv_lock_hash_differs_by_venv_mode(self):
        base_dict = self._base_config_dict()
        shared_requirements = ["pre-commit"]

        dev_config = MagicMock()
        dev_config.user_env.odpm_scenario = constants.DEVELOPER_SCENARIO
        dev_config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        dev_config.requirements_txt = list(shared_requirements)
        self._apply_lock_hash_fields(dev_config, base_dict)

        ci_config = MagicMock()
        ci_config.user_env.odpm_scenario = constants.CI_SCENARIO
        ci_config.policy = ScenarioPolicy.from_scenario(constants.CI_SCENARIO)
        ci_config.requirements_txt = list(shared_requirements)
        self._apply_lock_hash_fields(ci_config, base_dict)

        self.assertNotEqual(
            compute_venv_lock_hash(dev_config),
            compute_venv_lock_hash(ci_config),
        )

    def test_config_to_json_includes_scenario_and_venv_mode(self):
        config = MagicMock()
        config.user_env.odpm_scenario = constants.SERVER_SCENARIO
        config.policy = ScenarioPolicy.from_scenario(constants.SERVER_SCENARIO)
        config.docker_odoo_dir = "/home/odoo/odoo"
        config.odoo_config_data = {}
        config.docker_path_odoo_conf = "/home/odoo/odoo.conf"
        config.arguments = Namespace()
        config.db_creation_data = constants.DEFAULT_DB_CREATION_DATA
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
        config.container_run_mode = constants.RUN_MODE_ODOO

        payload = json.loads(config_to_json(config).decode("utf-8"))
        self.assertEqual(payload["schema_version"], CONTAINER_CONFIG_SCHEMA_VERSION)
        self.assertEqual(payload["venv_mode"], constants.VENV_MODE_FRESH)
        self.assertEqual(payload["odpm_scenario"], constants.SERVER_SCENARIO)
        self.assertEqual(payload["run_mode"], constants.RUN_MODE_ODOO)

    def test_config_class_methods_accept_mock_like_test_virtualenv_checker(self):
        base_dict = self._base_config_dict()
        mock_config = MagicMock()
        mock_config.user_env.odpm_scenario = constants.DEVELOPER_SCENARIO
        mock_config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        mock_config.requirements_txt = ["pre-commit"]
        self._apply_lock_hash_fields(mock_config, base_dict)

        self.assertTrue(Config.compute_venv_lock_hash(mock_config))


class ConfigBootstrapTests(unittest.TestCase):
    def test_get_odpm_settings_reads_odpm_json_from_cloned_repo(self):
        with tempfile.TemporaryDirectory() as project_dir:
            dev_path = os.path.join(project_dir, "dev_repo")
            os.makedirs(dev_path)
            odpm_content = {
                "odoo_version": "17.0",
                "python_version": "3.10",
                "odpm_version": constants.ODPM_VERSION,
            }
            odpm_path = os.path.join(dev_path, constants.PROJECT_CONFIG_FILE_NAME)
            Path(odpm_path).write_text(json.dumps(odpm_content), encoding="utf-8")

            config = Config.__new__(Config)
            config._raw_user_settings = {}
            config._raw_odpm_json = {}
            config._user = UserSettingsState()
            config._project = ProjectSettingsState()
            config._user_loaded = False
            config._project_loaded = False
            config.project_dir = project_dir
            config.developing_project = MagicMock(project_path=dev_path)
            config.repo_odpm_json = ""
            config.project_odpm_json = os.path.join(
                project_dir, constants.PROJECT_CONFIG_FILE_NAME
            )

            ConfigLoader(config).get_project_odpm_json()
            ConfigLoader(config).get_odpm_settings()

            self.assertEqual(config._raw_odpm_json["odoo_version"], "17.0")
            self.assertEqual(config._raw_odpm_json["python_version"], "3.10")


class ConfigStateSliceTests(unittest.TestCase):
    def test_slice_property_facade_reads_and_writes(self):
        config = Config.__new__(Config)
        config._user = UserSettingsState()
        config._project = ProjectSettingsState()
        config._docker = DockerLayoutState()

        config.init_modules = "sale,purchase"
        config.odoo_version = "19.0"
        config.docker_project_dir = "/home/odoo"

        self.assertEqual(config._user.init_modules, "sale,purchase")
        self.assertEqual(config._project.odoo_version, "19.0")
        self.assertEqual(config._docker.docker_project_dir, "/home/odoo")
        self.assertEqual(config.user_settings.init_modules, "sale,purchase")
        self.assertEqual(config.project_settings.odoo_version, "19.0")
        self.assertEqual(config.docker_layout.docker_project_dir, "/home/odoo")

    def test_seed_dependency_urls_reads_odpm_json(self):
        config = Config.__new__(Config)
        config._raw_odpm_json = {
            "dependencies": [
                "https://github.com/OCA/partner-contact.git",
                "  ",
                "",
            ]
        }

        self.assertEqual(
            config.seed_dependency_urls(),
            ["https://github.com/OCA/partner-contact.git"],
        )

    def test_load_user_settings_populates_user_slice(self):
        config = Config.__new__(Config)
        config._raw_user_settings = {
            "init_modules": ["sale", "purchase"],
            "developing_project": "https://github.com/acme/demo.git",
        }
        config._user = UserSettingsState()
        config._loader = MagicMock()
        config._loader.beautify_module_list.side_effect = ConfigLoader(config).beautify_module_list

        load_user_settings(config)

        self.assertEqual(config._user.init_modules, "sale,purchase")
        self.assertEqual(
            config._user.developing_project, "https://github.com/acme/demo.git"
        )
        self.assertTrue(config._user_loaded)

    def test_load_project_settings_populates_project_slice(self):
        config = Config.__new__(Config)
        config._raw_odpm_json = {
            "odoo_version": "18.0",
            "python_version": "3.12",
            "platform_name": "odoo",
            "odpm_version": constants.ODPM_VERSION,
        }
        config.arguments = Namespace(
            odoo_version=None,
            python_version=None,
            distro_name=None,
            distro_version=None,
            postgres_version=None,
            requirements_txt="",
        )
        config._project = ProjectSettingsState()
        config._loader = MagicMock()
        config._loader.get_effective_odoo_build_date.return_value = (
            constants.ODOO_DEFAULT_BUILD_DATE
        )
        config.repo_odpm_json = "/tmp/project/odpm.json"
        config.pd_manager = MagicMock(
            project_docker_compose_template_path="/tmp/project/.odpm/docker-compose.yml"
        )

        load_project_settings(config)

        self.assertEqual(config._project.odoo_version, "18.0")
        self.assertEqual(config._project.python_version, "3.12")
        self.assertEqual(config._project.platform_name, "odoo")
        self.assertTrue(config._project_loaded)


class ConfigApplyTransitiveRequirementsTests(unittest.TestCase):
    def _config(self, *, scenario: str = constants.DEVELOPER_SCENARIO) -> Config:
        config = Config.__new__(Config)
        config._user = UserSettingsState()
        config._project = ProjectSettingsState(
            odoo_version="17.0",
            python_version="3.12",
            requirements_txt=["requests==2.31.0"],
        )
        config.policy = ScenarioPolicy.from_scenario(scenario)
        return config

    def test_merges_transitive_requirements_and_renormalizes(self):
        config = self._config()
        config.apply_transitive_requirements(
            ["openupgradelib", "requests==2.31.0"],
        )
        expected_debugpy = config.policy.debugpy_requirement("3.12")
        self.assertEqual(
            config.requirements_txt,
            ["requests==2.31.0", "openupgradelib", expected_debugpy],
        )

    def test_dev_mode_reload_adds_inotify_to_requirements(self):
        config = self._config()
        config._user.dev_mode = "all"
        normalized = config._normalize_project_requirements(["requests==2.31.0"])
        self.assertIn(constants.ODOO_AUTORELOAD_INOTIFY_REQUIREMENT, normalized)
        self.assertIn(
            config.policy.debugpy_requirement("3.12"),
            normalized,
        )

    def test_dev_mode_reload_ignored_in_server_scenario(self):
        config = self._config(scenario=constants.SERVER_SCENARIO)
        config._user.dev_mode = "all"
        normalized = config._normalize_project_requirements(["requests==2.31.0"])
        self.assertNotIn(constants.ODOO_AUTORELOAD_INOTIFY_REQUIREMENT, normalized)
        self.assertNotIn(
            config.policy.debugpy_requirement("3.12"),
            normalized,
        )

    def test_version_mismatch_warns_in_developer_scenario(self):
        config = self._config()
        fragment = NestedOdpmFragment(
            dependencies=[],
            requirements_txt=[],
            odoo_version="19.0",
            python_version=None,
            source_path="/tmp/framework/odpm.json",
        )
        with patch("dev_project.config.config._logger") as mock_logger:
            config.apply_transitive_requirements([], nested_fragments=[fragment])
        mock_logger.warning.assert_called_once()
        mock_logger.error.assert_not_called()

    def test_version_mismatch_fails_in_ci_scenario(self):
        config = self._config(scenario=constants.CI_SCENARIO)
        fragment = NestedOdpmFragment(
            dependencies=[],
            requirements_txt=[],
            odoo_version="19.0",
            python_version=None,
            source_path="/tmp/framework/odpm.json",
        )
        with self.assertRaises(PipelineError):
            config.apply_transitive_requirements([], nested_fragments=[fragment])


if __name__ == "__main__":
    unittest.main()
