import json
import os
import tempfile
import unittest
from dev_project.host.cli.args import OdpmCliArgs
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.container_config import (
    CONTAINER_CONFIG_SCHEMA_VERSION,
    ContainerConfig,
    load_container_config_from_env,
    load_container_config_from_path,
)
from dev_project.inside_docker_app.exceptions import ConfigValidationError, ContainerError
from dev_project.scenario_policy import ScenarioPolicy

from tests.container_config_helpers import (
    apply_odpm_config_database_fields,
    minimal_container_config_dict,
)


class ContainerConfigFromDictTests(unittest.TestCase):
    def test_round_trip_to_json_bytes(self):
        payload = minimal_container_config_dict(
            odpm_scenario=constants.SERVER_SCENARIO,
            venv_mode=constants.VENV_MODE_FRESH,
        )
        config = ContainerConfig.from_dict(payload)
        raw = config.to_json_bytes().decode("utf-8")
        self.assertIn("\n    ", raw)
        self.assertTrue(raw.endswith("\n"))
        decoded = json.loads(raw)
        self.assertEqual(decoded["schema_version"], CONTAINER_CONFIG_SCHEMA_VERSION)
        self.assertEqual(decoded["odpm_scenario"], constants.SERVER_SCENARIO)
        self.assertEqual(decoded["venv_mode"], constants.VENV_MODE_FRESH)

    def test_legacy_v0_without_schema_version_or_run_mode(self):
        payload = minimal_container_config_dict()
        payload.pop("schema_version", None)
        payload.pop("run_mode", None)
        config = ContainerConfig.from_dict(payload)
        self.assertEqual(config.schema_version, CONTAINER_CONFIG_SCHEMA_VERSION)
        self.assertEqual(config.run_mode, constants.RUN_MODE_ODOO)

    def test_legacy_v0_venv_mode_from_ci_scenario(self):
        payload = minimal_container_config_dict(
            odpm_scenario=constants.CI_SCENARIO,
        )
        payload.pop("venv_mode", None)
        config = ContainerConfig.from_dict(payload)
        self.assertEqual(config.venv_mode, constants.VENV_MODE_BAKED)

    def test_legacy_v0_venv_mode_from_developer_scenario(self):
        payload = minimal_container_config_dict(
            odpm_scenario=constants.DEVELOPER_SCENARIO,
        )
        payload.pop("venv_mode", None)
        config = ContainerConfig.from_dict(payload)
        self.assertEqual(config.venv_mode, constants.VENV_MODE_FRESH)

    def test_missing_required_field_raises(self):
        payload = minimal_container_config_dict()
        del payload["docker_venv_dir"]
        with self.assertRaises(ConfigValidationError):
            ContainerConfig.from_dict(payload)

    def test_invalid_venv_mode_raises(self):
        with self.assertRaises(ConfigValidationError):
            ContainerConfig.from_dict(
                minimal_container_config_dict(venv_mode="invalid")
            )

    def test_unsupported_schema_version_raises(self):
        with self.assertRaises(ConfigValidationError):
            ContainerConfig.from_dict(
                minimal_container_config_dict(schema_version=99)
            )


class ContainerConfigFromHostTests(unittest.TestCase):
    def test_from_odpm_config_includes_schema_version_and_run_mode(self):
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
        config.container_run_mode = constants.RUN_MODE_BOOTSTRAP_ONLY
        apply_odpm_config_database_fields(config)

        with patch(
            "dev_project.config.payload.compute_venv_lock_hash",
            return_value="lock-hash",
        ):
            container_config = ContainerConfig.from_odpm_config(config)

        self.assertEqual(
            container_config.schema_version, CONTAINER_CONFIG_SCHEMA_VERSION
        )
        self.assertEqual(container_config.run_mode, constants.RUN_MODE_BOOTSTRAP_ONLY)
        self.assertEqual(container_config.venv_mode, constants.VENV_MODE_FRESH)


class LoadContainerConfigTests(unittest.TestCase):
    def tearDown(self) -> None:
        os.environ.pop(constants.ODPM_CONFIG_PATH_ENV, None)

    def test_load_from_path(self):
        handle, path = tempfile.mkstemp(suffix=".json")
        os.close(handle)
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        payload = minimal_container_config_dict(
            odpm_scenario=constants.CI_SCENARIO,
            venv_mode=constants.VENV_MODE_BAKED,
        )
        Path(path).write_text(json.dumps(payload), encoding="utf-8")
        config = load_container_config_from_path(path)
        self.assertEqual(config.odpm_scenario, constants.CI_SCENARIO)

    def test_load_from_env_requires_file(self):
        with self.assertRaises(ContainerError):
            load_container_config_from_env()

    def test_load_from_env_uses_odpm_config_path(self):
        handle, path = tempfile.mkstemp(suffix=".json")
        os.close(handle)
        self.addCleanup(lambda: os.path.exists(path) and os.unlink(path))
        payload = minimal_container_config_dict()
        Path(path).write_text(json.dumps(payload), encoding="utf-8")
        os.environ[constants.ODPM_CONFIG_PATH_ENV] = path
        config = load_container_config_from_env()
        self.assertEqual(config.docker_project_dir, "/home/odoo")


if __name__ == "__main__":
    unittest.main()
