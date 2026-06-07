"""Contract tests for ContainerConfig v1 validation."""

import json
import unittest
from dev_project.host_cli.args import OdpmCliArgs
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.container_config import (
    CONTAINER_CONFIG_SCHEMA_VERSION,
    ContainerConfig,
    container_config_schema_v1,
    validate_container_config_dict,
)
from dev_project.inside_docker_app.exceptions import ConfigValidationError
from dev_project.scenario_policy import ScenarioPolicy

from tests.container_config_helpers import minimal_container_config_dict


class ContainerConfigSchemaTests(unittest.TestCase):
    def test_schema_file_loads(self):
        schema = container_config_schema_v1()
        self.assertEqual(schema["title"], "ContainerConfig")
        self.assertEqual(schema["properties"]["schema_version"]["const"], 1)

    def test_minimal_payload_passes_validation(self):
        payload = minimal_container_config_dict()
        validate_container_config_dict(payload)

    def test_missing_required_field_fails_validation(self):
        payload = minimal_container_config_dict()
        del payload["docker_venv_dir"]
        with self.assertRaises(ConfigValidationError):
            validate_container_config_dict(payload)

    def test_invalid_venv_mode_fails_validation(self):
        with self.assertRaises(ConfigValidationError):
            validate_container_config_dict(
                minimal_container_config_dict(venv_mode="invalid")
            )

    def test_unknown_field_fails_validation(self):
        payload = minimal_container_config_dict()
        payload["unexpected_key"] = True
        with self.assertRaises(ConfigValidationError) as ctx:
            validate_container_config_dict(payload)
        self.assertIn("unexpected_key", str(ctx.exception))

    def test_wrong_type_for_requirements_txt_fails_validation(self):
        with self.assertRaises(ConfigValidationError) as ctx:
            validate_container_config_dict(
                minimal_container_config_dict(requirements_txt="not-a-list")
            )
        self.assertIn("requirements_txt", str(ctx.exception))

    def test_unsupported_schema_version_fails_validation(self):
        with self.assertRaises(ConfigValidationError) as ctx:
            ContainerConfig.from_dict(minimal_container_config_dict(schema_version=99))
        self.assertIn("Unsupported container config schema_version", str(ctx.exception))

    def test_legacy_v0_normalizes_then_passes_validation(self):
        payload = minimal_container_config_dict()
        payload.pop("schema_version", None)
        payload.pop("run_mode", None)
        config = ContainerConfig.from_dict(payload)
        validate_container_config_dict(json.loads(config.to_json_bytes().decode("utf-8")))
        self.assertEqual(config.schema_version, CONTAINER_CONFIG_SCHEMA_VERSION)
        self.assertEqual(config.run_mode, constants.RUN_MODE_ODOO)

    def test_from_odpm_config_round_trip_passes_validation(self):
        config = MagicMock()
        config.user_env.odpm_scenario = constants.DEVELOPER_SCENARIO
        config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
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

        with patch(
            "dev_project.config.payload.compute_venv_lock_hash",
            return_value="lock-hash",
        ):
            container_config = ContainerConfig.from_odpm_config(config)

        payload = json.loads(container_config.to_json_bytes().decode("utf-8"))
        validate_container_config_dict(payload)
        self.assertEqual(payload["schema_version"], CONTAINER_CONFIG_SCHEMA_VERSION)


if __name__ == "__main__":
    unittest.main()
