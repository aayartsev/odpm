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

    def test_invalid_venv_mode_exits(self):
        with self.assertRaises(SystemExit):
            resolve_venv_mode(_config(venv_mode="invalid"))


class VirtualenvCheckerContractTests(unittest.TestCase):
    @patch("check_virtualenv.VirtualenvChecker.sync_extra_requirements")
    @patch("check_virtualenv.VirtualenvChecker.recreate_uv_venv")
    @patch("check_virtualenv.VirtualenvChecker.set_venv")
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

    @patch("check_virtualenv.VirtualenvChecker.sync_extra_requirements")
    @patch("check_virtualenv.VirtualenvChecker.recreate_uv_venv")
    @patch("check_virtualenv.VirtualenvChecker.set_venv")
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

    @patch("check_virtualenv.VirtualenvChecker.sync_extra_requirements")
    @patch("check_virtualenv.VirtualenvChecker.recreate_uv_venv")
    @patch("check_virtualenv.VirtualenvChecker.set_venv")
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


class BakedVenvFailureTests(unittest.TestCase):
    def _assert_baked_init_fails(self, config: dict) -> None:
        from check_virtualenv import VirtualenvChecker

        with self.assertRaises(SystemExit):
            VirtualenvChecker(config)

    def test_baked_missing_venv_dir_exits(self):
        with tempfile.TemporaryDirectory() as parent:
            missing_dir = str(Path(parent) / "no-venv")
            self._assert_baked_init_fails(
                _config(
                    docker_venv_dir=missing_dir,
                    venv_mode=constants.VENV_MODE_BAKED,
                )
            )

    def test_baked_missing_lock_file_exits(self):
        with tempfile.TemporaryDirectory() as venv_dir:
            self._assert_baked_init_fails(
                _config(
                    docker_venv_dir=venv_dir,
                    venv_mode=constants.VENV_MODE_BAKED,
                )
            )

    def test_baked_lock_hash_mismatch_exits(self):
        with tempfile.TemporaryDirectory() as venv_dir:
            lock_path = Path(venv_dir) / ".lock"
            lock_path.write_text("wrong-hash\n", encoding="utf-8")
            self._assert_baked_init_fails(
                _config(
                    docker_venv_dir=venv_dir,
                    venv_mode=constants.VENV_MODE_BAKED,
                )
            )


class VenvLockHashTests(unittest.TestCase):
    @staticmethod
    def _base_config_dict() -> dict:
        return {
            "python_version": "3.12",
            "distro_version": "12",
            "distro_name": "debian",
            "postgres_version": "15",
            "odoo_version": "19.0",
            "arch": "amd64",
        }

    def test_lock_hash_differs_when_normalized_requirements_differ(self):
        from dev_project.host_config import Config
        from dev_project.scenario_policy import ScenarioPolicy

        base_dict = self._base_config_dict()

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

    def test_lock_hash_differs_when_venv_mode_differs(self):
        from dev_project.host_config import Config

        base_dict = self._base_config_dict()
        shared_requirements = ["pre-commit", "requests==2.31.0"]

        dev_config = MagicMock()
        dev_config.user_env.odpm_scenario = constants.DEVELOPER_SCENARIO
        dev_config.requirements_txt = list(shared_requirements)
        dev_config.config_dict = dict(base_dict)

        ci_config = MagicMock()
        ci_config.user_env.odpm_scenario = constants.CI_SCENARIO
        ci_config.requirements_txt = list(shared_requirements)
        ci_config.config_dict = dict(base_dict)

        dev_hash = Config.compute_venv_lock_hash(dev_config)
        ci_hash = Config.compute_venv_lock_hash(ci_config)
        self.assertNotEqual(dev_hash, ci_hash)


if __name__ == "__main__":
    unittest.main()
