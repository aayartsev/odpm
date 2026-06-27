"""Tests for legacy database baseline adoption."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.database.adopt import (
    adopt_database_baseline,
    build_adoption_last_run,
    needs_database_adoption,
    start_postgres_detached,
    wait_for_postgres_ready,
)
from dev_project.database.schema import DATABASE_LAST_RUN_SCHEMA_VERSION
from dev_project.errors import OdpmError
from dev_project.scenario_policy import ScenarioPolicy


class NeedsDatabaseAdoptionTests(unittest.TestCase):
    def _config(self, project_dir: str, *, scenario: str = constants.DEVELOPER_SCENARIO):
        config = MagicMock()
        config.project_dir = project_dir
        config.policy = ScenarioPolicy.from_scenario(scenario)
        config.postgres_data_local_storage = os.path.join(
            project_dir, constants.POSTGRES_LOCAL_STORAGE_DIR
        )
        config.user_env.postgres_service_name = "db"
        config.user_env.postgres_port = 5432
        config.path_odoo_conf = os.path.join(project_dir, constants.ODOO_CONF_NAME)
        config.postgres_version = "17"
        return config

    def test_true_when_last_run_missing_on_developer_project(self):
        with tempfile.TemporaryDirectory() as project_dir:
            self.assertTrue(needs_database_adoption(self._config(project_dir)))

    def test_false_when_last_run_exists(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = self._config(project_dir)
            from dev_project.database.adopt import build_adoption_last_run
            from dev_project.database.state import save_last_run

            save_last_run(project_dir, build_adoption_last_run(config))
            self.assertFalse(needs_database_adoption(config))

    def test_false_on_ci_scenario(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = self._config(project_dir, scenario=constants.CI_SCENARIO)
            self.assertFalse(needs_database_adoption(config))


class AdoptDatabaseBaselineTests(unittest.TestCase):
    def _config(self, project_dir: str):
        config = MagicMock()
        config.project_dir = project_dir
        config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        config.docker_compose_command = "docker compose"
        config.postgres_data_local_storage = os.path.join(
            project_dir, constants.POSTGRES_LOCAL_STORAGE_DIR
        )
        config.user_env.postgres_service_name = "db"
        config.user_env.postgres_port = 5432
        config.path_odoo_conf = os.path.join(project_dir, constants.ODOO_CONF_NAME)
        config.postgres_version = "17"
        return config

    @patch("dev_project.database.adopt.save_last_run")
    @patch("dev_project.database.adopt.ensure_app_role")
    @patch("dev_project.database.adopt.probe_app_role_exists", return_value=False)
    @patch("dev_project.database.adopt.probe_postgres_ready", return_value=True)
    def test_adopts_when_postgres_already_ready(
        self,
        _mock_ready,
        _mock_role_exists,
        mock_ensure,
        mock_save,
    ):
        with tempfile.TemporaryDirectory() as project_dir:
            config = self._config(project_dir)
            mock_save.return_value = os.path.join(
                project_dir, constants.ODPM_DATABASE_LAST_RUN_REL_PATH
            )

            path = adopt_database_baseline(config)

            mock_ensure.assert_called_once_with(config)
            mock_save.assert_called_once()
            self.assertIsNotNone(path)
            saved_snapshot = mock_save.call_args[0][1]
            self.assertTrue(saved_snapshot.cluster.app_role_present)

    @patch("dev_project.database.adopt.save_last_run")
    @patch("dev_project.database.adopt.ensure_app_role")
    @patch("dev_project.database.adopt.wait_for_postgres_ready")
    @patch("dev_project.database.adopt.start_postgres_detached")
    @patch("dev_project.database.adopt.probe_app_role_exists", return_value=True)
    @patch("dev_project.database.adopt.probe_postgres_ready", return_value=False)
    def test_starts_postgres_when_not_ready(
        self,
        _mock_ready,
        _mock_role_exists,
        mock_start,
        mock_wait,
        mock_ensure,
        mock_save,
    ):
        with tempfile.TemporaryDirectory() as project_dir:
            config = self._config(project_dir)
            mock_save.return_value = "path"

            adopt_database_baseline(config)

            mock_start.assert_called_once_with(config)
            mock_wait.assert_called_once_with(config)
            mock_ensure.assert_called_once_with(config)

    def test_skips_when_last_run_exists(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = self._config(project_dir)
            from dev_project.database.state import save_last_run

            save_last_run(project_dir, build_adoption_last_run(config))
            self.assertIsNone(adopt_database_baseline(config))


class StartPostgresDetachedTests(unittest.TestCase):
    @patch("dev_project.database.adopt.compose_up_service_detached")
    def test_raises_when_compose_up_fails(self, mock_up):
        config = MagicMock()
        config.project_dir = "/tmp/project"
        config.docker_compose_command = "docker compose"
        config.user_env.postgres_service_name = "db"
        mock_up.return_value = MagicMock(returncode=1, stderr="boom", stdout="")

        with self.assertRaises(OdpmError):
            start_postgres_detached(config)


class WaitForPostgresReadyTests(unittest.TestCase):
    @patch("dev_project.database.adopt.time.sleep")
    @patch("dev_project.database.adopt.probe_postgres_ready", side_effect=[False, True])
    def test_waits_until_ready(self, _mock_probe, _mock_sleep):
        config = MagicMock()
        config.user_env.postgres_service_name = "db"
        wait_for_postgres_ready(config, timeout_seconds=5, poll_seconds=0)

    @patch("dev_project.database.adopt.time.sleep")
    @patch("dev_project.database.adopt.time.monotonic", side_effect=[0, 0, 10])
    @patch("dev_project.database.adopt.probe_postgres_ready", return_value=False)
    def test_raises_on_timeout(self, _mock_probe, _mock_monotonic, _mock_sleep):
        config = MagicMock()
        config.user_env.postgres_service_name = "db"
        with self.assertRaises(OdpmError):
            wait_for_postgres_ready(config, timeout_seconds=1, poll_seconds=0)


class BuildAdoptionLastRunTests(unittest.TestCase):
    def test_marks_app_role_present(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = MagicMock()
            config.project_dir = project_dir
            config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
            config.postgres_data_local_storage = os.path.join(
                project_dir, constants.POSTGRES_LOCAL_STORAGE_DIR
            )
            config.user_env.postgres_service_name = "db"
            config.user_env.postgres_port = 5432
            config.path_odoo_conf = os.path.join(project_dir, constants.ODOO_CONF_NAME)
            config.postgres_version = "17"

            snapshot = build_adoption_last_run(config)
            self.assertEqual(snapshot.schema_version, DATABASE_LAST_RUN_SCHEMA_VERSION)
            self.assertTrue(snapshot.cluster.app_role_present)


class RuntimeCoordinatorAdoptionTests(unittest.TestCase):
    @patch("dev_project.project_env.services.docker_base_image.BaseImageService.ensure_base_image")
    @patch("dev_project.runtime_coordinator.run_logged", return_value=0)
    @patch("dev_project.runtime_coordinator.RuntimeCoordinator.configure_ide")
    @patch("dev_project.runtime_coordinator.RuntimeCoordinator.write_debug_profile")
    @patch("dev_project.database.resolve.ensure_no_blocking_database_drift")
    @patch("dev_project.database.adopt.adopt_database_baseline")
    def test_run_after_prepare_adopts_before_compose(
        self, mock_adopt, mock_blocking, _mock_write, _mock_ide, _mock_run, _mock_base_image
    ):
        from dev_project.host.cli.args import OdpmCliArgs
        from dev_project.runtime_coordinator import RuntimeCoordinator

        config = MagicMock()
        config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        config.no_log_prefix = False
        config.project_dir = "/tmp/project"
        config.docker_compose_command = "docker compose"
        config.odoo_image_name = "odoo-base:test"
        config.user_env.odoo_port = 8069
        coordinator = RuntimeCoordinator(OdpmCliArgs(), config, MagicMock())

        with patch.object(
            coordinator, "build_compose_up_argv", return_value=["docker", "compose", "up"]
        ):
            coordinator.run_after_prepare()

        mock_adopt.assert_called_once_with(config)
        mock_blocking.assert_called_once_with(config, coordinator.cli_args)


if __name__ == "__main__":
    unittest.main()
