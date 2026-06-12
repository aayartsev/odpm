import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.config import Config
from dev_project.inside_docker_app.check_virtualenv import VirtualenvChecker
from dev_project.inside_docker_app.exceptions import ConfigValidationError, VenvError
from dev_project.inside_docker_app.utils import resolve_venv_mode
from dev_project.scenario_policy import ScenarioPolicy

from tests.container_config_helpers import minimal_container_config


class ResolveVenvModeTests(unittest.TestCase):
    def test_fresh_mode_from_config(self):
        self.assertEqual(
            resolve_venv_mode(
                minimal_container_config(venv_mode=constants.VENV_MODE_FRESH)
            ),
            constants.VENV_MODE_FRESH,
        )

    def test_baked_mode_from_config(self):
        self.assertEqual(
            resolve_venv_mode(
                minimal_container_config(venv_mode=constants.VENV_MODE_BAKED)
            ),
            constants.VENV_MODE_BAKED,
        )

    def test_invalid_venv_mode_raises(self):
        with self.assertRaises(ConfigValidationError) as ctx:
            resolve_venv_mode(minimal_container_config(venv_mode="invalid"))
        self.assertEqual(ctx.exception.exit_code, 1)


class VirtualenvCheckerContractTests(unittest.TestCase):
    @patch(
        "dev_project.inside_docker_app.check_virtualenv.VirtualenvChecker.sync_extra_requirements"
    )
    @patch(
        "dev_project.inside_docker_app.check_virtualenv.VirtualenvChecker.recreate_uv_venv"
    )
    @patch("dev_project.inside_docker_app.check_virtualenv.VirtualenvChecker.set_venv")
    def test_fresh_recreates_when_lock_mismatch(
        self, mock_set_venv, mock_recreate, mock_sync
    ):
        with tempfile.TemporaryDirectory() as venv_dir:
            lock_path = Path(venv_dir) / ".lock"
            lock_path.write_text("stale-hash\n", encoding="utf-8")
            config = minimal_container_config(
                docker_venv_dir=venv_dir,
                venv_mode=constants.VENV_MODE_FRESH,
                venv_lock_hash="expected-hash",
            )
            VirtualenvChecker(config)
            mock_recreate.assert_called_once()
            mock_sync.assert_called_once()
            mock_set_venv.assert_called()

    @patch(
        "dev_project.inside_docker_app.check_virtualenv.VirtualenvChecker.sync_extra_requirements"
    )
    @patch(
        "dev_project.inside_docker_app.check_virtualenv.VirtualenvChecker.recreate_uv_venv"
    )
    @patch("dev_project.inside_docker_app.check_virtualenv.VirtualenvChecker.set_venv")
    def test_fresh_skips_recreate_when_lock_matches(
        self, mock_set_venv, mock_recreate, mock_sync
    ):
        with tempfile.TemporaryDirectory() as venv_dir:
            lock_path = Path(venv_dir) / ".lock"
            lock_path.write_text("expected-hash\n", encoding="utf-8")
            config = minimal_container_config(
                docker_venv_dir=venv_dir,
                venv_mode=constants.VENV_MODE_FRESH,
                venv_lock_hash="expected-hash",
            )
            VirtualenvChecker(config)
            mock_recreate.assert_not_called()
            mock_sync.assert_called_once()

    @patch(
        "dev_project.inside_docker_app.check_virtualenv.VirtualenvChecker.sync_extra_requirements"
    )
    @patch(
        "dev_project.inside_docker_app.check_virtualenv.VirtualenvChecker.recreate_uv_venv"
    )
    @patch("dev_project.inside_docker_app.check_virtualenv.VirtualenvChecker.set_venv")
    def test_baked_never_recreates_or_syncs_extras(
        self, mock_set_venv, mock_recreate, mock_sync
    ):
        with tempfile.TemporaryDirectory() as venv_dir:
            lock_path = Path(venv_dir) / ".lock"
            lock_path.write_text("expected-hash\n", encoding="utf-8")
            config = minimal_container_config(
                docker_venv_dir=venv_dir,
                venv_mode=constants.VENV_MODE_BAKED,
                venv_lock_hash="expected-hash",
            )
            VirtualenvChecker(config)
            mock_recreate.assert_not_called()
            mock_sync.assert_not_called()
            mock_set_venv.assert_called_once()


class BakedVenvFailureTests(unittest.TestCase):
    def _assert_baked_init_fails(self, config) -> None:
        with self.assertRaises(VenvError) as ctx:
            VirtualenvChecker(config)
        self.assertEqual(ctx.exception.exit_code, 1)

    def test_baked_missing_venv_dir_exits(self):
        with tempfile.TemporaryDirectory() as parent:
            missing_dir = str(Path(parent) / "no-venv")
            self._assert_baked_init_fails(
                minimal_container_config(
                    docker_venv_dir=missing_dir,
                    venv_mode=constants.VENV_MODE_BAKED,
                    venv_lock_hash="expected-hash",
                )
            )

    def test_baked_missing_lock_file_exits(self):
        with tempfile.TemporaryDirectory() as venv_dir:
            self._assert_baked_init_fails(
                minimal_container_config(
                    docker_venv_dir=venv_dir,
                    venv_mode=constants.VENV_MODE_BAKED,
                    venv_lock_hash="expected-hash",
                )
            )

    def test_baked_lock_hash_mismatch_exits(self):
        with tempfile.TemporaryDirectory() as venv_dir:
            lock_path = Path(venv_dir) / ".lock"
            lock_path.write_text("wrong-hash\n", encoding="utf-8")
            self._assert_baked_init_fails(
                minimal_container_config(
                    docker_venv_dir=venv_dir,
                    venv_mode=constants.VENV_MODE_BAKED,
                    venv_lock_hash="expected-hash",
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

    @classmethod
    def _apply_lock_hash_fields(cls, config: MagicMock, base_dict: dict) -> None:
        for key, value in base_dict.items():
            setattr(config, key, value)

    def test_lock_hash_differs_when_normalized_requirements_differ(self):
        base_dict = self._base_config_dict()

        dev_config = MagicMock()
        dev_config.user_env.odpm_scenario = constants.DEVELOPER_SCENARIO
        dev_config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        dev_config.requirements_txt = ScenarioPolicy.from_scenario(
            constants.DEVELOPER_SCENARIO
        ).normalize_requirements(["pre-commit"], python_version="3.12")
        self._apply_lock_hash_fields(dev_config, base_dict)

        server_config = MagicMock()
        server_config.user_env.odpm_scenario = constants.SERVER_SCENARIO
        server_config.policy = ScenarioPolicy.from_scenario(constants.SERVER_SCENARIO)
        server_config.requirements_txt = ScenarioPolicy.from_scenario(
            constants.SERVER_SCENARIO
        ).normalize_requirements(
            ["pre-commit", "debugpy==9.9.9"], python_version="3.12"
        )
        self._apply_lock_hash_fields(server_config, base_dict)

        dev_hash = Config.compute_venv_lock_hash(dev_config)
        server_hash = Config.compute_venv_lock_hash(server_config)
        self.assertNotEqual(dev_hash, server_hash)

    def test_lock_hash_differs_when_venv_mode_differs(self):
        base_dict = self._base_config_dict()
        shared_requirements = ["pre-commit", "requests==2.31.0"]

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

        dev_hash = Config.compute_venv_lock_hash(dev_config)
        ci_hash = Config.compute_venv_lock_hash(ci_config)
        self.assertNotEqual(dev_hash, ci_hash)


class SyncExtraRequirementsHygieneTests(unittest.TestCase):
    def _checker(self, **overrides) -> VirtualenvChecker:
        use_uv = overrides.pop("use_uv", True)
        requirements_txt = overrides.pop("requirements_txt", ["requests==2.31.0"])
        config = minimal_container_config(
            requirements_txt=requirements_txt,
            **overrides,
        )
        checker = VirtualenvChecker.__new__(VirtualenvChecker)
        checker.config = config
        checker.docker_project_dir = config.docker_project_dir
        checker.docker_venv_dir = config.docker_venv_dir
        checker.python_version = config.python_version
        checker.requirements_txt = config.requirements_txt
        checker.use_uv = use_uv
        checker._run_pip_command = MagicMock()
        return checker

    def test_list_installed_packages_uv_invalid_json_raises_venv_error(self):
        checker = self._checker()
        with patch(
            "dev_project.inside_docker_app.check_virtualenv.subprocess.run"
        ) as mock_run:
            mock_run.return_value = MagicMock(
                stdout=b"not-json",
                stderr=b"",
                returncode=0,
            )
            with self.assertRaises(VenvError) as ctx:
                checker._list_installed_packages()
        self.assertIn("invalid JSON", str(ctx.exception))

    def test_list_installed_packages_non_uv_uses_venv_pip_freeze(self):
        checker = self._checker(use_uv=False)
        with patch(
            "dev_project.inside_docker_app.check_virtualenv.subprocess.run"
        ) as mock_run:
            mock_run.return_value = MagicMock(
                stdout=b"requests==2.31.0\npip==24.0\n",
                stderr=b"",
                returncode=0,
            )
            packages = checker._list_installed_packages()
        mock_run.assert_called_once_with(
            ["/home/odoo/.venv/bin/python3", "-m", "pip", "freeze"],
            capture_output=True,
            cwd=checker.docker_project_dir,
            check=False,
        )
        self.assertEqual(
            packages,
            [
                {"name": "requests", "version": "2.31.0"},
                {"name": "pip", "version": "24.0"},
            ],
        )

    def test_sync_extra_requirements_non_uv_does_not_chdir_or_run_subprocess(self):
        checker = self._checker(use_uv=False)
        with patch(
            "dev_project.inside_docker_app.check_virtualenv.os.chdir"
        ) as mock_chdir:
            with patch(
                "dev_project.inside_docker_app.check_virtualenv.subprocess.run"
            ) as mock_run:
                with patch.object(
                    checker,
                    "_list_installed_packages",
                    return_value=[{"name": "requests", "version": "2.31.0"}],
                ):
                    with patch.object(
                        checker, "check_package_to_install", return_value=[]
                    ):
                        checker.sync_extra_requirements()
        mock_chdir.assert_not_called()
        mock_run.assert_not_called()
        checker._run_pip_command.assert_not_called()

    def test_sync_extra_requirements_uv_uses_list_argv_without_chdir(self):
        checker = self._checker()
        installed = [{"name": "requests", "version": "2.31.0"}]

        with patch(
            "dev_project.inside_docker_app.check_virtualenv.os.chdir"
        ) as mock_chdir:
            with patch(
                "dev_project.inside_docker_app.check_virtualenv.subprocess.run"
            ) as mock_run:
                mock_run.return_value = MagicMock(
                    stdout=json.dumps(installed).encode("utf-8"),
                    stderr=b"",
                    returncode=0,
                )
                with patch.object(
                    checker, "check_package_to_install", return_value=[]
                ):
                    checker.sync_extra_requirements()

        mock_chdir.assert_not_called()
        mock_run.assert_called_once_with(
            [
                "uv",
                "pip",
                "list",
                "--format",
                "json",
                "--python",
                "/home/odoo/.venv/bin/python3",
            ],
            capture_output=True,
            cwd=checker.docker_project_dir,
            check=False,
        )
        checker._run_pip_command.assert_not_called()

    def test_sync_extra_requirements_uv_install_targets_venv_python(self):
        checker = self._checker(requirements_txt=["debugpy==1.7.0"])
        with patch.object(
            checker,
            "_list_installed_packages",
            return_value=[],
        ):
            with patch.object(
                checker,
                "check_package_to_install",
                return_value=[
                    {"command": "install", "name": "debugpy", "version": "1.7.0"},
                ],
            ):
                checker.sync_extra_requirements()
        checker._run_pip_command.assert_called_once_with(
            [
                "uv",
                "pip",
                "install",
                "--link-mode=copy",
                "--python",
                "/home/odoo/.venv/bin/python3",
                "debugpy==1.7.0",
            ]
        )


class CheckPackageToInstallTests(unittest.TestCase):
    def _checker(self) -> VirtualenvChecker:
        config = minimal_container_config()
        checker = VirtualenvChecker.__new__(VirtualenvChecker)
        checker.config = config
        return checker

    def test_extras_requirement_matches_installed_distribution(self):
        checker = self._checker()
        installed = [{"name": "zeep", "version": "4.2.1"}]
        instructions = checker.check_package_to_install(
            "zeep[async]==4.2.1", installed
        )
        self.assertEqual(instructions, [])

    def test_extras_requirement_requests_install_when_missing(self):
        checker = self._checker()
        instructions = checker.check_package_to_install("zeep[async]==4.2.1", [])
        self.assertEqual(len(instructions), 1)
        self.assertEqual(instructions[0]["command"], "install")
        self.assertEqual(instructions[0]["name"], "zeep[async]")
        self.assertEqual(instructions[0]["version"], "4.2.1")


if __name__ == "__main__":
    unittest.main()
