import json
import os
import tempfile
import unittest
from dev_project.host.cli.args import OdpmCliArgs
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.config import Config, compute_venv_lock_hash, config_to_json
from tests.container_config_helpers import apply_odpm_config_database_fields
from dev_project.container_config import CONTAINER_CONFIG_SCHEMA_VERSION
from dev_project.config.bootstrap import (
    bind_developing_link,
    bind_platform_link,
    init_context,
    load_project_settings,
    load_user_settings,
)
from dev_project.config.artifacts import DeprecatedConfigHandler
from dev_project.config.bootstrap_context import ConfigBootstrapContext
from dev_project.config.defaults import ConfigDefaultsFactory
from dev_project.config.manifests import OdpmJsonReader, UserSettingsReader, rewrite_odpm_json
from dev_project.config.transforms import (
    EnvResolver,
    OdooBuildDateResolver,
    beautify_module_list,
)
from dev_project.config.git_repos import GitRepoCoordinator
from dev_project.config.odoo_conf import OdooConfBuilder
from dev_project.config.paths import ConfigPaths
from dev_project.config.state import (
    AddonLayoutState,
    BootstrapState,
    DockerLayoutState,
    ProjectSettingsState,
    UserSettingsState,
)
from dev_project.errors import ConfigError, PipelineError
from dev_project.ide_stubs import odoo_stubs_pip_requirement
from dev_project.scenario_policy import ScenarioPolicy
from dev_project.dependency_resolver import NestedOdpmFragment


class ConfigTransformsTests(unittest.TestCase):
    def test_beautify_module_list_from_comma_string(self):
        self.assertEqual(
            beautify_module_list(" sale , purchase "),
            "sale,purchase",
        )

    def test_beautify_module_list_empty_returns_default(self):
        self.assertEqual(
            beautify_module_list(None),
            constants.DEFAULT_LIST_OF_MODULES,
        )

    def test_beautify_module_list_from_list(self):
        self.assertEqual(
            beautify_module_list([" sale ", "purchase"]),
            "sale,purchase",
        )

    def test_get_effective_odoo_build_date_prefers_cli(self):
        config = MagicMock()
        config.arguments = OdpmCliArgs(
            odoo_build_date=" 2024-01-15 ",
            odoo_version=None,
            python_version=None,
            distro_name=None,
            distro_version=None,
            postgres_version=None,
            requirements_txt="",
        )
        config._raw_odpm_json = {"odoo_build_date": "2023-01-01"}
        self.assertEqual(
            OdooBuildDateResolver(config).get_effective_odoo_build_date(),
            "2024-01-15",
        )

    def test_get_effective_odoo_build_date_falls_back_to_raw_json(self):
        config = MagicMock()
        config.arguments = OdpmCliArgs(
            odoo_version=None,
            python_version=None,
            distro_name=None,
            distro_version=None,
            postgres_version=None,
            requirements_txt="",
        )
        config._raw_odpm_json = {"odoo_build_date": " 2023-06-01 "}
        self.assertEqual(
            OdooBuildDateResolver(config).get_effective_odoo_build_date(),
            "2023-06-01",
        )

    def test_get_effective_odoo_build_date_empty_when_unset(self):
        config = MagicMock()
        config.arguments = OdpmCliArgs(
            odoo_version=None,
            python_version=None,
            distro_name=None,
            distro_version=None,
            postgres_version=None,
            requirements_txt="",
        )
        config._raw_odpm_json = {}
        self.assertEqual(
            OdooBuildDateResolver(config).get_effective_odoo_build_date(),
            "",
        )


class OdpmJsonWriterTests(unittest.TestCase):
    def test_rewrite_odpm_json_writes_default_manifest(self):
        with tempfile.TemporaryDirectory() as project_dir:
            dev_path = os.path.join(project_dir, "dev_repo")
            config = MagicMock()
            config.developing_project = MagicMock(project_path=dev_path)
            config.repo_odpm_json = os.path.join(
                dev_path, constants.PROJECT_CONFIG_FILE_NAME
            )
            default_content = {
                "odoo_version": "19.0",
                "odpm_version": constants.MANIFEST_V1_CONTRACT_LINE,
            }
            create_default = MagicMock(return_value=default_content)
            rewrite_odpm_json(config, create_default=create_default)

            create_default.assert_called_once()
            self.assertTrue(os.path.exists(config.repo_odpm_json))
            self.assertEqual(
                json.loads(Path(config.repo_odpm_json).read_text(encoding="utf-8")),
                default_content,
            )


class ConfigPathsTests(unittest.TestCase):
    def test_get_odoo_ci_image_name_uses_image_tag_when_set(self):
        config = MagicMock()
        config.arguments = OdpmCliArgs(image_tag=" custom:tag ")
        config.odoo_version = "19.0"
        config.platform_name = "odoo"
        self.assertEqual(
            ConfigPaths(config).get_odoo_ci_image_name(),
            "custom:tag",
        )

    def test_get_odoo_ci_image_name_default_pattern(self):
        config = MagicMock()
        config.arguments = OdpmCliArgs()
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
        config.docker_layout = DockerLayoutState()
        config.user_env = MagicMock(backups="/tmp/backups")
        config.odoo_src_dir = "/tmp/odoo"
        config.developing_project_dir_path = "/tmp/dev"
        config.repo_odpm_json = "/tmp/dev/odpm.json"
        config.create_module_links = False
        ConfigPaths(config).apply_symlink_sources()
        self.assertEqual(
            config.docker_layout.list_for_symlinks.count("/tmp/dev/odpm.json"), 1
        )

    def test_apply_symlink_sources_no_duplicate_when_create_module_links_true(self):
        config = MagicMock()
        config.docker_layout = DockerLayoutState()
        config.user_env = MagicMock(backups="/tmp/backups")
        config.odoo_src_dir = "/tmp/odoo"
        config.developing_project_dir_path = "/tmp/dev"
        config.repo_odpm_json = "/tmp/dev/odpm.json"
        config.create_module_links = True
        ConfigPaths(config).apply_symlink_sources()
        self.assertEqual(
            config.docker_layout.list_for_symlinks.count("/tmp/dev/odpm.json"), 1
        )
        self.assertEqual(len(config.docker_layout.list_for_symlinks), 4)

    def test_apply_docker_layout_developer_uses_host_identity(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = MagicMock()
            config.docker_layout = DockerLayoutState()
            config.project_dir = project_dir
            config.platform_name = constants.PLATFORM_NAME
            config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
            runtime_user = config.policy.runtime_unix_user()

            ConfigPaths(config).apply_docker_layout()

            self.assertEqual(
                config.docker_layout.docker_project_dir, f"/home/{runtime_user}"
            )
            expected_home = os.path.join(
                project_dir, "data/odoo", f"home/{runtime_user}"
            )
            self.assertEqual(config.docker_layout.dir_for_odoo_container_home, expected_home)
            self.assertTrue(os.path.isdir(os.path.join(expected_home, ".cache")))
            self.assertTrue(os.path.isdir(os.path.join(expected_home, ".local")))

    def test_apply_docker_layout_ci_uses_container_identity(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = MagicMock()
            config.docker_layout = DockerLayoutState()
            config.project_dir = project_dir
            config.platform_name = constants.PLATFORM_NAME
            config.policy = ScenarioPolicy.from_scenario(constants.CI_SCENARIO)

            ConfigPaths(config).apply_docker_layout()

            self.assertEqual(config.docker_layout.docker_project_dir, "/home/odoo")
            expected_home = os.path.join(project_dir, "data/odoo", "home/odoo")
            self.assertEqual(config.docker_layout.dir_for_odoo_container_home, expected_home)
            self.assertTrue(os.path.isdir(os.path.join(expected_home, ".cache")))


class ConfigDefaultsFactoryTests(unittest.TestCase):
    def test_get_developing_project_link_from_legacy_config_json(self):
        config = MagicMock()
        config.config_json_content = {
            "developing_project": "https://github.com/acme/demo.git"
        }
        config.pd_manager = MagicMock(init=".", project_path="/tmp/project")
        link = ConfigDefaultsFactory(config).get_developing_project_link()
        self.assertEqual(link, "https://github.com/acme/demo.git")

    def test_get_developing_project_link_wraps_relative_init_path(self):
        config = MagicMock()
        config.config_json_content = {}
        config.pd_manager = MagicMock(init="my_repo", project_path="/tmp/project")
        link = ConfigDefaultsFactory(config).get_developing_project_link()
        self.assertEqual(link, "file:///tmp/project/my_repo")

    def test_create_default_user_settings_check_system_true_by_default(self):
        config = MagicMock()
        config.config_json_content = {}
        config.pd_manager = MagicMock(init=".", project_path="/tmp/project")
        content = ConfigDefaultsFactory(config).create_default_user_setting_json_content()
        self.assertTrue(content["check_system"])

    @patch("dev_project.config.defaults.factory.stdin_is_interactive", return_value=False)
    def test_create_default_odpm_json_raises_without_odoo_version(self, _mock_tty):
        config = MagicMock()
        config.config_json_content = {}
        config.arguments = OdpmCliArgs(odoo_version=None)
        config._raw_odpm_json = {}

        with self.assertRaises(ConfigError):
            ConfigDefaultsFactory(config).create_default_odpm_json_content()

    @patch("dev_project.config.defaults.factory.stdin_is_interactive", return_value=False)
    def test_create_default_odpm_json_uses_cli_odoo_version(self, _mock_tty):
        config = MagicMock()
        config.config_json_content = {}
        config.arguments = OdpmCliArgs(
            odoo_version="18.0",
            python_version=None,
            distro_name=None,
            distro_version=None,
            postgres_version=None,
            requirements_txt="",
            odoo_git_link=None,
            platform_name=None,
        )
        config._raw_odpm_json = {"odpm_version": constants.MANIFEST_V1_CONTRACT_LINE}

        content = ConfigDefaultsFactory(config).create_default_odpm_json_content()

        self.assertEqual(content["odoo_version"], "18.0")


class DeprecatedConfigHandlerTests(unittest.TestCase):
    def test_check_for_config_renames_legacy_config_json(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = MagicMock()
            config.project_dir = project_dir
            config.config_json_content = {}
            config.config_json_path = ""
            config.config_deprecated_json_path = ""

            legacy_path = os.path.join(project_dir, constants.CONFIG_FILE_NAME)
            Path(legacy_path).write_text('{"init_modules": []}', encoding="utf-8")

            DeprecatedConfigHandler(config).check_for_config()

            self.assertFalse(os.path.exists(legacy_path))
            deprecated_path = os.path.join(
                project_dir, f"deprecated_{constants.CONFIG_FILE_NAME}"
            )
            self.assertTrue(os.path.exists(deprecated_path))
            self.assertEqual(config.config_json_content, {"init_modules": []})

    def test_check_file_for_deprecated_words_renames_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "docker-compose.yml")
            with open(path, "w", encoding="utf-8") as writer:
                writer.write("services:\n  {DEBUGGER_PORT_MAP}:\n")

            DeprecatedConfigHandler(MagicMock()).check_file_for_deprecated_words(path)

            self.assertFalse(os.path.exists(path))
            self.assertTrue(
                os.path.exists(os.path.join(tmp_dir, "deprecated_docker-compose.yml"))
            )

    def test_check_file_for_deprecated_words_noop_when_file_missing(self):
        handler = DeprecatedConfigHandler(MagicMock())
        handler.check_file_for_deprecated_words("/tmp/does-not-exist-odpm-test.yml")


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
        config.arguments = OdpmCliArgs()
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
        apply_odpm_config_database_fields(config)

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


class OdpmJsonReaderTests(unittest.TestCase):
    def test_get_odpm_settings_reads_odpm_json_from_cloned_repo(self):
        with tempfile.TemporaryDirectory() as project_dir:
            dev_path = os.path.join(project_dir, "dev_repo")
            os.makedirs(dev_path)
            odpm_content = {
                "odoo_version": "17.0",
                "python_version": "3.10",
                "odpm_version": constants.MANIFEST_V1_CONTRACT_LINE,
            }
            odpm_path = os.path.join(dev_path, constants.PROJECT_CONFIG_FILE_NAME)
            Path(odpm_path).write_text(json.dumps(odpm_content), encoding="utf-8")

            config = MagicMock()
            config._raw_odpm_json = {}
            config.project_dir = project_dir
            config.developing_project = MagicMock(project_path=dev_path)
            config.repo_odpm_json = ""
            config.project_odpm_json = os.path.join(
                project_dir, constants.PROJECT_CONFIG_FILE_NAME
            )
            config.env_resolver = EnvResolver.from_sources(
                process_environ={},
                project_dotenv={},
            )
            rewrite_mock = MagicMock()

            reader = OdpmJsonReader(config, rewrite_odpm_json=rewrite_mock)
            reader.get_project_odpm_json()
            reader.get_odpm_settings()

            rewrite_mock.assert_not_called()
            self.assertEqual(config.repo_odpm_json, odpm_path)
            self.assertEqual(config._raw_odpm_json["odoo_version"], "17.0")
            self.assertEqual(config._raw_odpm_json["python_version"], "3.10")

    def test_get_odpm_settings_expands_env_refs_in_whitelist_fields(self):
        with tempfile.TemporaryDirectory() as project_dir:
            dev_path = os.path.join(project_dir, "dev_repo")
            os.makedirs(dev_path)
            odpm_content = {
                "odoo_version": "17.${ODOO_VER}",
                "odpm_version": constants.MANIFEST_V1_CONTRACT_LINE,
                "odoo_git_link": "file://${ODOO_PLATFORM_DIR}",
                "dependencies": [
                    "file://${OCA_WEB_PATH}",
                    "https://github.com/OCA/sale.git 17.0",
                ],
            }
            odpm_path = os.path.join(dev_path, constants.PROJECT_CONFIG_FILE_NAME)
            Path(odpm_path).write_text(json.dumps(odpm_content), encoding="utf-8")

            config = MagicMock()
            config._raw_odpm_json = {}
            config.project_dir = project_dir
            config.developing_project = MagicMock(project_path=dev_path)
            config.repo_odpm_json = odpm_path
            config.project_odpm_json = os.path.join(
                project_dir, constants.PROJECT_CONFIG_FILE_NAME
            )
            config.env_resolver = EnvResolver.from_sources(
                process_environ={"GIT_HOST": "git.process.example"},
                project_dotenv={
                    "ODOO_PLATFORM_DIR": "/home/dev/odoo/17.0",
                    "OCA_WEB_PATH": "/home/dev/oca/web",
                },
            )

            OdpmJsonReader(config, rewrite_odpm_json=MagicMock()).get_odpm_settings()

            self.assertEqual(config._raw_odpm_json["odoo_version"], "17.${ODOO_VER}")
            self.assertEqual(
                config._raw_odpm_json["odoo_git_link"],
                "file:///home/dev/odoo/17.0",
            )
            self.assertEqual(
                config._raw_odpm_json["dependencies"],
                [
                    "file:///home/dev/oca/web",
                    "https://github.com/OCA/sale.git 17.0",
                ],
            )

    def test_get_odpm_settings_missing_env_var_raises_config_error(self):
        with tempfile.TemporaryDirectory() as project_dir:
            dev_path = os.path.join(project_dir, "dev_repo")
            os.makedirs(dev_path)
            odpm_path = os.path.join(dev_path, constants.PROJECT_CONFIG_FILE_NAME)
            Path(odpm_path).write_text(
                json.dumps({"odoo_git_link": "file://${MISSING}"}),
                encoding="utf-8",
            )

            config = MagicMock()
            config._raw_odpm_json = {}
            config.repo_odpm_json = odpm_path
            config.project_odpm_json = os.path.join(
                project_dir, constants.PROJECT_CONFIG_FILE_NAME
            )
            config.env_resolver = EnvResolver.from_sources(
                process_environ={},
                project_dotenv={},
            )

            with self.assertRaises(ConfigError) as ctx:
                OdpmJsonReader(config, rewrite_odpm_json=MagicMock()).get_odpm_settings()

            self.assertIn("MISSING", str(ctx.exception))
            self.assertIn("odoo_git_link", str(ctx.exception))

    def test_get_project_odpm_json_invokes_rewrite_when_manifests_missing(self):
        with tempfile.TemporaryDirectory() as project_dir:
            dev_path = os.path.join(project_dir, "dev_repo")
            os.makedirs(dev_path)
            config = MagicMock()
            config.project_dir = project_dir
            config.developing_project = MagicMock(project_path=dev_path)
            rewrite_mock = MagicMock()

            OdpmJsonReader(config, rewrite_odpm_json=rewrite_mock).get_project_odpm_json()

            rewrite_mock.assert_called_once()


class UserSettingsReaderTests(unittest.TestCase):
    def test_get_user_settings_loads_existing_json(self):
        with tempfile.TemporaryDirectory() as project_dir:
            settings_path = os.path.join(
                project_dir, constants.USER_CONFIG_FILE_NAME
            )
            Path(settings_path).write_text(
                json.dumps({"init_modules": ["sale"]}),
                encoding="utf-8",
            )
            config = Config.__new__(Config)
            config.project_dir = project_dir
            config._raw_user_settings = {}
            config.user_settings_json = settings_path
            config._env_resolver = EnvResolver.from_sources(
                process_environ={},
                project_dotenv={},
            )

            UserSettingsReader(
                config,
                create_default_user_settings=MagicMock(),
            ).get_user_settings()

            self.assertEqual(config._raw_user_settings, {"init_modules": ["sale"]})

    def test_get_user_settings_expands_developing_project_env_ref(self):
        with tempfile.TemporaryDirectory() as project_dir:
            settings_path = os.path.join(
                project_dir, constants.USER_CONFIG_FILE_NAME
            )
            Path(settings_path).write_text(
                json.dumps(
                    {
                        "developing_project": "file://${DEVELOPING_DIR}",
                        "init_modules": ["sale"],
                    }
                ),
                encoding="utf-8",
            )
            config = Config.__new__(Config)
            config.project_dir = project_dir
            config._raw_user_settings = {}
            config.user_settings_json = settings_path
            config._env_resolver = EnvResolver.from_sources(
                process_environ={},
                project_dotenv={"DEVELOPING_DIR": "/home/dev/my_addons"},
            )

            UserSettingsReader(
                config,
                create_default_user_settings=MagicMock(),
            ).get_user_settings()

            self.assertEqual(
                config._raw_user_settings["developing_project"],
                "file:///home/dev/my_addons",
            )
            self.assertEqual(config._raw_user_settings["init_modules"], ["sale"])

    def test_get_user_settings_json_creates_file_via_default_factory(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = Config.__new__(Config)
            config.project_dir = project_dir
            create_default = MagicMock(return_value={"init_modules": "sale"})

            UserSettingsReader(
                config,
                create_default_user_settings=create_default,
            ).get_user_settings_json()

            create_default.assert_called_once()
            settings_path = os.path.join(
                project_dir, constants.USER_CONFIG_FILE_NAME
            )
            self.assertTrue(os.path.exists(settings_path))
            self.assertEqual(
                json.loads(Path(settings_path).read_text(encoding="utf-8")),
                {"init_modules": "sale"},
            )


class ConfigBootstrapContextWiringTests(unittest.TestCase):
    def test_bootstrap_context_wires_all_services(self):
        config = MagicMock()
        ctx = ConfigBootstrapContext(config)

        self.assertIsInstance(ctx.defaults, ConfigDefaultsFactory)
        self.assertIsInstance(ctx.deprecated, DeprecatedConfigHandler)
        self.assertIsInstance(ctx.build_date, OdooBuildDateResolver)
        self.assertIsInstance(ctx.user_settings, UserSettingsReader)
        self.assertIsInstance(ctx.odpm_json, OdpmJsonReader)

    def test_bootstrap_context_rewrite_odpm_json_delegates_to_writer(self):
        config = MagicMock()
        ctx = ConfigBootstrapContext(config)
        with patch(
            "dev_project.config.manifests.odpm_json_writer.rewrite_odpm_json"
        ) as mock_rewrite:
            ctx.rewrite_odpm_json()
        mock_rewrite.assert_called_once_with(
            config,
            create_default=ctx.defaults.create_default_odpm_json_write_payload,
        )

    def test_bootstrap_context_wires_host_services(self):
        config = MagicMock()
        bind_platform_link = MagicMock()
        ctx = ConfigBootstrapContext(
            config,
            bind_platform_link=bind_platform_link,
        )

        self.assertIsInstance(ctx.paths, ConfigPaths)
        self.assertIsInstance(ctx.odoo_conf, OdooConfBuilder)
        self.assertIsInstance(ctx.git_repos, GitRepoCoordinator)
        self.assertIs(ctx.git_repos._paths, ctx.paths)
        self.assertIs(ctx.git_repos._bind_platform_link, bind_platform_link)


class ConfigBootstrapStateTests(unittest.TestCase):
    def test_init_context_creates_bootstrap_state(self):
        config = Config.__new__(Config)
        init_context(
            config,
            MagicMock(project_path="/tmp/project"),
            OdpmCliArgs(
                odoo_version=None,
                python_version=None,
                distro_name=None,
                distro_version=None,
                postgres_version=None,
                requirements_txt="",
            ),
            "/tmp/odpm",
            MagicMock(odpm_scenario=constants.DEVELOPER_SCENARIO),
        )

        self.assertIsInstance(config.bootstrap, BootstrapState)
        self.assertIsInstance(config.addon_layout, AddonLayoutState)
        self.assertEqual(config.bootstrap.raw_user_settings, {})
        self.assertEqual(config.bootstrap.raw_odpm_json, {})
        self.assertFalse(config.bootstrap.user_loaded)
        self.assertFalse(config.bootstrap.project_loaded)
        self.assertEqual(config.bootstrap.repo_odpm_json, "")

    def test_init_context_creates_env_resolver_from_user_env(self):
        config = Config.__new__(Config)
        user_env = MagicMock(odpm_scenario=constants.DEVELOPER_SCENARIO)
        user_env.project_dotenv_dict.return_value = {
            "ODOO_PLATFORM_DIR": "/from/dotenv",
            "GIT_HOST": "git.dotenv.example",
        }
        with patch.dict(
            os.environ,
            {
                "ODOO_PLATFORM_DIR": "/from/process",
            },
            clear=False,
        ):
            init_context(
                config,
                MagicMock(project_path="/tmp/project"),
                OdpmCliArgs(
                    odoo_version=None,
                    python_version=None,
                    distro_name=None,
                    distro_version=None,
                    postgres_version=None,
                    requirements_txt="",
                ),
                "/tmp/odpm",
                user_env,
            )

        self.assertIsInstance(config.env_resolver, EnvResolver)
        self.assertEqual(config.env_resolver.resolve("ODOO_PLATFORM_DIR"), "/from/process")
        self.assertEqual(config.env_resolver.resolve("GIT_HOST"), "git.dotenv.example")
        user_env.project_dotenv_dict.assert_called_once_with()

    def test_property_shims_delegate_to_bootstrap(self):
        config = Config.__new__(Config)
        config._bootstrap = BootstrapState()

        config._raw_odpm_json = {"odoo_version": "18.0"}
        config.repo_odpm_json = "/tmp/project/odpm.json"
        config._user_loaded = True

        self.assertEqual(config.bootstrap.raw_odpm_json, {"odoo_version": "18.0"})
        self.assertEqual(config.bootstrap.repo_odpm_json, "/tmp/project/odpm.json")
        self.assertTrue(config.bootstrap.user_loaded)

    def test_developing_project_lives_in_bootstrap_not_user_slice(self):
        config = Config.__new__(Config)
        config._bootstrap = BootstrapState()
        config._user = UserSettingsState(developing_project="https://github.com/acme/demo.git")

        config.developing_project = MagicMock(project_path="/tmp/dev")

        self.assertIs(config.bootstrap.developing_project, config.developing_project)
        self.assertEqual(
            config._user.developing_project, "https://github.com/acme/demo.git"
        )

    def test_load_user_settings_syncs_developing_project_to_bootstrap(self):
        config = Config.__new__(Config)
        config._bootstrap = BootstrapState()
        config._raw_user_settings = {
            "developing_project": "https://github.com/acme/demo.git",
        }
        config._user = UserSettingsState()
        config._bootstrap_ctx = MagicMock()

        load_user_settings(config)

        self.assertEqual(
            config.bootstrap.developing_project, "https://github.com/acme/demo.git"
        )
        self.assertTrue(config.bootstrap.user_loaded)


class BindDevelopingLinkTests(unittest.TestCase):
    def test_bind_developing_link_raises_when_developing_project_missing(self):
        config = Config.__new__(Config)
        config._user = UserSettingsState()
        config.developing_project = ""

        with self.assertRaises(ConfigError):
            bind_developing_link(config)


class BindPlatformLinkTests(unittest.TestCase):
    def test_bind_platform_link_sets_platform_project_and_src_dir(self):
        config = Config.__new__(Config)
        config._project = ProjectSettingsState()
        config.odoo_git_link = "https://github.com/odoo/odoo.git"
        platform_link = MagicMock()
        platform_link.get_project_path.return_value = "/tmp/odoo/src"
        config.handle_git_link = MagicMock(return_value=platform_link)

        bind_platform_link(config)

        config.handle_git_link.assert_called_once_with(
            config.odoo_git_link,
            system_type="platform",
            materialize=False,
        )
        self.assertIs(config.odoo_platform_project, platform_link)
        self.assertEqual(config.odoo_src_dir, "/tmp/odoo/src")


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

    def test_addon_layout_property_facade_reads_and_writes(self):
        config = Config.__new__(Config)
        config._addon_layout = AddonLayoutState()

        config.catalogs_of_modules_data = [{"name": "demo"}]
        config.list_of_developing_project_subprojects_data = [{"rel": "addons"}]

        self.assertEqual(config.addon_layout.catalogs_of_modules_data, [{"name": "demo"}])
        self.assertEqual(
            config.addon_layout.list_of_developing_project_subprojects_data,
            [{"rel": "addons"}],
        )

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
        config._bootstrap_ctx = MagicMock()

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
            "odpm_version": constants.MANIFEST_V1_CONTRACT_LINE,
        }
        config.arguments = OdpmCliArgs(
            odoo_version=None,
            python_version=None,
            distro_name=None,
            distro_version=None,
            postgres_version=None,
            requirements_txt="",
        )
        config._project = ProjectSettingsState()
        ctx = MagicMock()
        ctx.build_date = OdooBuildDateResolver(config)
        config._bootstrap_ctx = ctx
        config._raw_odpm_json["odoo_build_date"] = constants.ODOO_DEFAULT_BUILD_DATE
        config.repo_odpm_json = "/tmp/project/odpm.json"
        config.pd_manager = MagicMock(
            project_docker_compose_template_path="/tmp/project/.odpm/docker-compose.yml"
        )

        with patch("dev_project.config.bootstrap_phases.os.path.exists", return_value=True):
            load_project_settings(config)

        ctx.odpm_json.get_project_odpm_json.assert_called_once()
        ctx.odpm_json.get_odpm_settings.assert_called_once()
        self.assertEqual(ctx.deprecated.check_file_for_deprecated_words.call_count, 2)
        ctx.rewrite_odpm_json.assert_not_called()
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
        config.user_env = MagicMock()
        config.user_env.debugger_backend = "debugpy_listen"
        return config

    def test_merges_transitive_requirements_and_renormalizes(self):
        config = self._config()
        config.apply_transitive_requirements(
            ["openupgradelib", "requests==2.31.0"],
        )
        expected_debugpy = config.policy.debugpy_requirement("3.12")
        expected_stubs = odoo_stubs_pip_requirement("17.0")
        self.assertEqual(
            config.requirements_txt,
            ["requests==2.31.0", "openupgradelib", expected_debugpy, expected_stubs],
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
        with self.assertLogs("dev_project.config.config", level="WARNING") as captured:
            config.apply_transitive_requirements([], nested_fragments=[fragment])
        self.assertEqual(len(captured.output), 1)
        self.assertIn("19.0", captured.output[0])
        self.assertIn("17.0", captured.output[0])

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
