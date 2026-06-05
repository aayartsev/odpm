import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
INSIDE_DOCKER_APP = PROJECT_ROOT / "dev_project" / "inside_docker_app"
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(INSIDE_DOCKER_APP))

from dev_project import constants
from dev_project.inside_docker_app.utils import resolve_venv_is_baked, resolve_venv_mode


def _minimal_config(**overrides) -> dict:
    base = {
        "docker_venv_dir": "/home/odoo/.venv",
        "docker_project_dir": "/home/odoo",
        "docker_odoo_dir": "/home/odoo/odoo",
        "requirements_txt": [],
        "python_version": "3.12",
        "venv_lock_hash": "abc",
        "arch": "amd64",
    }
    base.update(overrides)
    return base


class ResolveVenvIsBakedTests(unittest.TestCase):
    def test_venv_mode_baked(self):
        self.assertTrue(
            resolve_venv_is_baked(_minimal_config(venv_mode=constants.VENV_MODE_BAKED))
        )

    def test_venv_mode_fresh(self):
        self.assertFalse(
            resolve_venv_is_baked(_minimal_config(venv_mode=constants.VENV_MODE_FRESH))
        )

    def test_legacy_ci_scenario_fallback(self):
        self.assertTrue(
            resolve_venv_is_baked(
                _minimal_config(odpm_scenario=constants.CI_SCENARIO)
            )
        )

    def test_legacy_developer_scenario_fallback(self):
        self.assertFalse(
            resolve_venv_is_baked(
                _minimal_config(odpm_scenario=constants.DEVELOPER_SCENARIO)
            )
        )

    def test_venv_mode_takes_priority_over_legacy_scenario(self):
        self.assertFalse(
            resolve_venv_is_baked(
                _minimal_config(
                    venv_mode=constants.VENV_MODE_FRESH,
                    odpm_scenario=constants.CI_SCENARIO,
                )
            )
        )


class ResolveVenvModeTests(unittest.TestCase):
    def test_resolve_venv_mode_matches_policy(self):
        self.assertEqual(
            resolve_venv_mode(_minimal_config(venv_mode=constants.VENV_MODE_BAKED)),
            constants.VENV_MODE_BAKED,
        )


class PrepareVenvTests(unittest.TestCase):
    @patch("container_bootstrap.VirtualenvChecker")
    def test_prepare_venv_uses_config_venv_mode(self, checker_cls):
        from container_bootstrap import prepare_venv

        config = _minimal_config(venv_mode=constants.VENV_MODE_BAKED)
        prepare_venv(config)
        checker_cls.assert_called_once_with(config)


if __name__ == "__main__":
    unittest.main()
