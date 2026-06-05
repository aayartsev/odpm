import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INSIDE_DOCKER_APP = PROJECT_ROOT / "dev_project" / "inside_docker_app"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(INSIDE_DOCKER_APP))

from dev_project import constants
from dev_project.inside_docker_app.utils import resolve_venv_mode


def _config(**overrides) -> dict:
    base = {
        "docker_venv_dir": "/home/odoo/.venv",
        "docker_project_dir": "/home/odoo",
        "docker_odoo_dir": "/home/odoo/odoo",
        "requirements_txt": [],
        "python_version": "3.12",
        "venv_lock_hash": "expected-hash",
        "arch": "amd64",
    }
    base.update(overrides)
    return base


class ResolveVenvModeTests(unittest.TestCase):
    def test_fresh_mode_from_config(self):
        self.assertEqual(
            resolve_venv_mode(_config(venv_mode=constants.VENV_MODE_FRESH)),
            constants.VENV_MODE_FRESH,
        )

    def test_baked_mode_from_config(self):
        self.assertEqual(
            resolve_venv_mode(_config(venv_mode=constants.VENV_MODE_BAKED)),
            constants.VENV_MODE_BAKED,
        )


class VirtualenvCheckerContractTests(unittest.TestCase):
    @patch.object(
        __import__("check_virtualenv", fromlist=["VirtualenvChecker"]).VirtualenvChecker,
        "sync_extra_requirements",
    )
    @patch.object(
        __import__("check_virtualenv", fromlist=["VirtualenvChecker"]).VirtualenvChecker,
        "recreate_uv_venv",
    )
    @patch.object(
        __import__("check_virtualenv", fromlist=["VirtualenvChecker"]).VirtualenvChecker,
        "set_venv",
    )
    def test_fresh_recreates_when_lock_mismatch(
        self, mock_set_venv, mock_recreate, mock_sync
    ):
        from check_virtualenv import VirtualenvChecker

        with tempfile.TemporaryDirectory() as venv_dir:
            lock_path = Path(venv_dir) / ".lock"
            lock_path.write_text("stale-hash\n", encoding="utf-8")
            config = _config(
                docker_venv_dir=venv_dir,
                venv_mode=constants.VENV_MODE_FRESH,
            )
            VirtualenvChecker(config)
            mock_recreate.assert_called_once()
            mock_sync.assert_called_once()
            mock_set_venv.assert_called()

    @patch.object(
        __import__("check_virtualenv", fromlist=["VirtualenvChecker"]).VirtualenvChecker,
        "sync_extra_requirements",
    )
    @patch.object(
        __import__("check_virtualenv", fromlist=["VirtualenvChecker"]).VirtualenvChecker,
        "recreate_uv_venv",
    )
    @patch.object(
        __import__("check_virtualenv", fromlist=["VirtualenvChecker"]).VirtualenvChecker,
        "set_venv",
    )
    def test_fresh_skips_recreate_when_lock_matches(
        self, mock_set_venv, mock_recreate, mock_sync
    ):
        from check_virtualenv import VirtualenvChecker

        with tempfile.TemporaryDirectory() as venv_dir:
            lock_path = Path(venv_dir) / ".lock"
            lock_path.write_text("expected-hash\n", encoding="utf-8")
            config = _config(
                docker_venv_dir=venv_dir,
                venv_mode=constants.VENV_MODE_FRESH,
            )
            VirtualenvChecker(config)
            mock_recreate.assert_not_called()
            mock_sync.assert_called_once()

    @patch.object(
        __import__("check_virtualenv", fromlist=["VirtualenvChecker"]).VirtualenvChecker,
        "sync_extra_requirements",
    )
    @patch.object(
        __import__("check_virtualenv", fromlist=["VirtualenvChecker"]).VirtualenvChecker,
        "recreate_uv_venv",
    )
    @patch.object(
        __import__("check_virtualenv", fromlist=["VirtualenvChecker"]).VirtualenvChecker,
        "set_venv",
    )
    def test_baked_never_recreates_or_syncs_extras(
        self, mock_set_venv, mock_recreate, mock_sync
    ):
        from check_virtualenv import VirtualenvChecker

        with tempfile.TemporaryDirectory() as venv_dir:
            lock_path = Path(venv_dir) / ".lock"
            lock_path.write_text("expected-hash\n", encoding="utf-8")
            config = _config(
                docker_venv_dir=venv_dir,
                venv_mode=constants.VENV_MODE_BAKED,
            )
            VirtualenvChecker(config)
            mock_recreate.assert_not_called()
            mock_sync.assert_not_called()
            mock_set_venv.assert_called_once()


class VenvLockHashTests(unittest.TestCase):
    def test_lock_hash_reflects_requirements_and_scenario(self):
        from dev_project.host_config import Config
        from dev_project.scenario_policy import ScenarioPolicy

        base_dict = {
            "python_version": "3.12",
            "distro_version": "12",
            "distro_name": "debian",
            "postgres_version": "15",
            "odoo_version": "19.0",
            "arch": "amd64",
        }

        dev_config = MagicMock()
        dev_config.user_env.odpm_scenario = constants.DEVELOPER_SCENARIO
        dev_config.requirements_txt = ScenarioPolicy.from_scenario(
            constants.DEVELOPER_SCENARIO
        ).normalize_requirements(["pre-commit"], python_version="3.12")
        dev_config.config_dict = dict(base_dict)

        server_config = MagicMock()
        server_config.user_env.odpm_scenario = constants.SERVER_SCENARIO
        server_config.requirements_txt = ScenarioPolicy.from_scenario(
            constants.SERVER_SCENARIO
        ).normalize_requirements(
            ["pre-commit", "debugpy==9.9.9"], python_version="3.12"
        )
        server_config.config_dict = dict(base_dict)

        dev_hash = Config.compute_venv_lock_hash(dev_config)
        server_hash = Config.compute_venv_lock_hash(server_config)
        self.assertNotEqual(dev_hash, server_hash)


if __name__ == "__main__":
    unittest.main()
