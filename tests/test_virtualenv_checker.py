import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.config import Config
from dev_project.config.payload import compute_extras_stamp
from dev_project.inside_docker_app.check_virtualenv import VirtualenvChecker
from dev_project.inside_docker_app.exceptions import ConfigValidationError, VenvError
from dev_project.inside_docker_app.extras_sync import write_extras_lock
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
    def setUp(self) -> None:
        self._verify_import_patch = patch(
            "dev_project.inside_docker_app.check_virtualenv.verify_venv_import_smoke",
            return_value=True,
        )
        self._verify_import_patch.start()

    def tearDown(self) -> None:
        self._verify_import_patch.stop()

    @patch(
        "dev_project.inside_docker_app.check_virtualenv.VirtualenvChecker.sync_extras_requirements"
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
            mock_sync.assert_not_called()
            mock_set_venv.assert_called()

    @patch(
        "dev_project.inside_docker_app.check_virtualenv.VirtualenvChecker.sync_extras_requirements"
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
        "dev_project.inside_docker_app.check_virtualenv.VirtualenvChecker.sync_extras_requirements"
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

    @patch(
        "dev_project.inside_docker_app.check_virtualenv.verify_venv_import_smoke",
    )
    @patch(
        "dev_project.inside_docker_app.check_virtualenv.VirtualenvChecker.sync_extras_requirements"
    )
    @patch(
        "dev_project.inside_docker_app.check_virtualenv.VirtualenvChecker.recreate_uv_venv"
    )
    @patch("dev_project.inside_docker_app.check_virtualenv.VirtualenvChecker.set_venv")
    def test_fresh_recreates_when_import_smoke_fails(
        self, mock_set_venv, mock_recreate, mock_sync, mock_verify
    ):
        mock_verify.side_effect = [False, True]
        with tempfile.TemporaryDirectory() as venv_dir:
            lock_path = Path(venv_dir) / ".lock"
            lock_path.write_text("expected-hash\n", encoding="utf-8")
            config = minimal_container_config(
                docker_venv_dir=venv_dir,
                venv_mode=constants.VENV_MODE_FRESH,
                venv_lock_hash="expected-hash",
            )
            VirtualenvChecker(config)
            mock_sync.assert_called_once()
            mock_recreate.assert_called_once()
            self.assertEqual(mock_verify.call_count, 2)


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
        if not getattr(config, "docker_odoo_dir", None):
            config.docker_odoo_dir = ""

    def test_lock_hash_same_when_only_requirements_differ(self):
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
        self.assertEqual(dev_hash, server_hash)
        self.assertNotEqual(
            compute_extras_stamp(dev_config.requirements_txt),
            compute_extras_stamp(server_config.requirements_txt),
        )

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


class ExtrasSyncIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        self._verify_import_patch = patch(
            "dev_project.inside_docker_app.check_virtualenv.verify_venv_import_smoke",
            return_value=True,
        )
        self._verify_import_patch.start()

    def tearDown(self) -> None:
        self._verify_import_patch.stop()

    def test_adding_one_extra_package_does_not_recreate_venv(self):
        base_hash = "expected-base-hash"
        old_requirements = ["requests==2.31.0"]
        old_stamp = compute_extras_stamp(old_requirements)

        with tempfile.TemporaryDirectory() as venv_dir:
            Path(venv_dir, ".lock").write_text(f"{base_hash}\n", encoding="utf-8")
            write_extras_lock(
                str(Path(venv_dir) / constants.VENV_EXTRAS_LOCK_BASENAME),
                stamp=old_stamp,
                distributions=["requests"],
            )
            config = minimal_container_config(
                docker_venv_dir=venv_dir,
                venv_mode=constants.VENV_MODE_FRESH,
                venv_lock_hash=base_hash,
                requirements_txt=[*old_requirements, "debugpy==1.7.0"],
            )

            with patch.object(
                VirtualenvChecker, "recreate_uv_venv"
            ) as mock_recreate:
                with patch(
                    "dev_project.bake_venv.create_venv"
                ) as mock_create_venv:
                    with patch.object(
                        VirtualenvChecker, "_run_pip_command"
                    ) as mock_pip:
                        VirtualenvChecker(config)

            mock_recreate.assert_not_called()
            mock_create_venv.assert_not_called()
            mock_pip.assert_called_once()
            install_argv = mock_pip.call_args.args[0]
            self.assertIn("-r", install_argv)
            self.assertIn(
                constants.VENV_EXTRAS_REQUIREMENTS_BASENAME,
                install_argv[-1],
            )

    def test_sync_extras_uninstalls_removed_managed_package(self):
        base_hash = "expected-base-hash"
        old_requirements = ["requests==2.31.0", "debugpy==1.7.0"]
        old_stamp = compute_extras_stamp(old_requirements)

        with tempfile.TemporaryDirectory() as venv_dir:
            Path(venv_dir, ".lock").write_text(f"{base_hash}\n", encoding="utf-8")
            write_extras_lock(
                str(Path(venv_dir) / constants.VENV_EXTRAS_LOCK_BASENAME),
                stamp=old_stamp,
                distributions=["debugpy", "requests"],
            )
            config = minimal_container_config(
                docker_venv_dir=venv_dir,
                venv_mode=constants.VENV_MODE_FRESH,
                venv_lock_hash=base_hash,
                requirements_txt=["requests==2.31.0"],
            )
            checker = VirtualenvChecker.__new__(VirtualenvChecker)
            checker.config = config
            checker.docker_venv_dir = venv_dir
            checker.docker_project_dir = config.docker_project_dir
            checker.requirements_txt = config.requirements_txt
            checker.extras_lock_file_path = str(
                Path(venv_dir) / constants.VENV_EXTRAS_LOCK_BASENAME
            )
            checker.extras_requirements_path = str(
                Path(venv_dir) / constants.VENV_EXTRAS_REQUIREMENTS_BASENAME
            )
            checker.use_uv = True
            checker._run_pip_command = MagicMock()

            checker.sync_extras_requirements()

            checker._run_pip_command.assert_any_call(
                [
                    "uv",
                    "pip",
                    "uninstall",
                    "--python",
                    checker._venv_python,
                    "debugpy",
                ]
            )


if __name__ == "__main__":
    unittest.main()
