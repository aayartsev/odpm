import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project.bake_venv import (
    PipRunner,
    VenvInstallSpec,
    _make_pip_runner,
    activate_venv,
    apply_venv_env,
    create_venv,
    install_fresh,
    install_odoo_requirement_packages,
    main,
    materialize_odoo_requirements_path,
    patch_odoo_requirements_gevent_line,
    patch_odoo_requirements_libsass_line,
    resolve_gevent_requirement,
    resolve_libsass_requirement,
    run_pip_command,
)
from dev_project import constants
from dev_project.inside_docker_app.exceptions import VenvError


def _spec(**overrides) -> VenvInstallSpec:
    base = {
        "project_dir": "/tmp/project",
        "venv_dir": "/tmp/project/.venv",
        "odoo_requirements_path": "/tmp/project/odoo/requirements.txt",
        "extra_packages": [],
        "python_version": "3.12",
    }
    base.update(overrides)
    return VenvInstallSpec(**base)


class RunPipCommandTests(unittest.TestCase):
    @patch("dev_project.bake_venv.subprocess.run")
    def test_run_pip_command_uses_argv_without_shell(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0)

        run_pip_command("python3 -m pip install wheel", cwd="/tmp/project")

        mock_run.assert_called_once()
        cmd, kwargs = mock_run.call_args
        self.assertEqual(
            cmd[0],
            ["python3", "-m", "pip", "install", "wheel"],
        )
        self.assertNotIn("shell", kwargs)
        self.assertEqual(kwargs["cwd"], "/tmp/project")

    @patch("dev_project.bake_venv.subprocess.run")
    def test_run_pip_command_failure_raises_venv_error(self, mock_run):
        mock_run.return_value = MagicMock(returncode=17)

        with self.assertRaises(VenvError) as ctx:
            run_pip_command("uv pip install requests --link-mode=copy", cwd="/tmp")

        self.assertEqual(ctx.exception.exit_code, 17)


class PipRunnerTests(unittest.TestCase):
    @patch("dev_project.bake_venv._run_subprocess")
    def test_install_odoo_requirement_packages_installs_implicit_packages(self, mock_run):
        pip = PipRunner(base_cmd=["uv"], pip_extra_args=["--link-mode=copy"], cwd="/home/odoo")
        from dev_project.bake_venv import install_odoo_requirement_packages

        install_odoo_requirement_packages(
            ["wheel"],
            pip,
            "/home/odoo/requirements.txt",
            python_version="3.12",
        )
        mock_run.assert_called()
        install_calls = [call.args[0] for call in mock_run.call_args_list]
        self.assertTrue(
            any("decorator" in cmd for cmd in install_calls),
            msg=f"expected implicit decorator install, got: {install_calls}",
        )

    @patch("dev_project.bake_venv._run_subprocess")
    def test_install_builds_list_argv(self, mock_run):
        pip = PipRunner(base_cmd=["uv"], pip_extra_args=["--link-mode=copy"], cwd="/home/odoo")
        pip.install("setuptools", "wheel")
        mock_run.assert_called_once_with(
            ["uv", "pip", "install", "--link-mode=copy", "setuptools", "wheel"],
            cwd="/home/odoo",
        )

    def test_make_pip_runner_uv_targets_venv_python(self):
        spec = _spec(venv_dir="/home/odoo/.venv")
        runner = _make_pip_runner(spec, use_uv=True)
        self.assertEqual(
            runner.pip_extra_args,
            ["--link-mode=copy", "--python", "/home/odoo/.venv/bin/python3"],
        )

    def test_make_pip_runner_pip_targets_venv_python(self):
        spec = _spec(venv_dir="/home/odoo/.venv")
        runner = _make_pip_runner(spec, use_uv=False)
        self.assertEqual(runner.base_cmd, ["/home/odoo/.venv/bin/python3", "-m"])


class ApplyVenvEnvTests(unittest.TestCase):
    def test_apply_venv_env_sets_virtual_env(self):
        with tempfile.TemporaryDirectory() as venv_dir:
            bin_dir = os.path.join(venv_dir, "bin")
            os.makedirs(bin_dir)
            python_path = os.path.join(bin_dir, "python3")
            Path(python_path).touch()
            apply_venv_env(venv_dir)
            self.assertEqual(os.environ["VIRTUAL_ENV"], venv_dir)
            self.assertTrue(os.environ["PATH"].startswith(bin_dir + os.pathsep))


class ActivateVenvTests(unittest.TestCase):
    @patch("dev_project.bake_venv.apply_venv_env")
    @patch("dev_project.bake_venv._find_file", return_value="/tmp/.venv/bin/activate")
    def test_activate_venv_calls_apply_venv_env(self, _mock_find, mock_apply):
        spec = _spec(venv_dir="/tmp/.venv", python_version="3.12")
        activate_venv(spec)
        mock_apply.assert_called_once_with("/tmp/.venv", python_version="3.12")


class InstallFreshTests(unittest.TestCase):
    @patch("dev_project.bake_venv.install_extra_packages")
    @patch("dev_project.bake_venv.install_odoo_requirement_packages")
    @patch("dev_project.bake_venv.bootstrap_packages")
    @patch("dev_project.bake_venv.parse_odoo_requirements", return_value=["wheel"])
    @patch("dev_project.bake_venv.activate_venv")
    @patch("dev_project.bake_venv.create_venv")
    @patch("dev_project.bake_venv.detect_uv", return_value=False)
    @patch("dev_project.bake_venv.os.chdir")
    def test_install_fresh_does_not_chdir(
        self,
        mock_chdir,
        _mock_uv,
        _mock_create,
        _mock_activate,
        _mock_parse,
        _mock_bootstrap,
        _mock_odoo_reqs,
        _mock_extras,
    ):
        with tempfile.TemporaryDirectory() as project_dir:
            odoo_dir = Path(project_dir) / "odoo"
            odoo_dir.mkdir()
            (odoo_dir / "requirements.txt").write_text("", encoding="utf-8")
            spec = _spec(
                project_dir=project_dir,
                venv_dir=str(Path(project_dir) / ".venv"),
                odoo_requirements_path=str(odoo_dir / "requirements.txt"),
            )
            install_fresh(spec, use_uv=False)
        mock_chdir.assert_not_called()


class CreateVenvTests(unittest.TestCase):
    @patch("dev_project.bake_venv.subprocess.run")
    def test_create_venv_uv_failure_raises_venv_error(self, mock_run):
        mock_run.return_value = MagicMock(returncode=3)
        spec = _spec()

        with self.assertRaises(VenvError) as ctx:
            create_venv(spec, use_uv=True)

        self.assertEqual(ctx.exception.exit_code, 3)
        mock_run.assert_called_once_with(
            ["uv", "venv", spec.venv_dir, "--python", sys.executable],
            cwd=spec.project_dir,
            check=False,
        )


class BakeVenvMainTests(unittest.TestCase):
    @patch("dev_project.bake_venv.install_fresh")
    @patch("dev_project.bake_venv.VenvInstallSpec.from_json_file")
    def test_main_exits_with_venv_error_code(self, mock_from_json, mock_install):
        from dev_project import bake_venv

        mock_from_json.return_value = _spec()
        mock_install.side_effect = VenvError("pip failed", exit_code=9)

        with patch.object(bake_venv.sys, "exit") as mock_exit:
            main(["--config", "ci/venv_install.json"])
            mock_exit.assert_called_once_with(9)


class ResolveGeventRequirementTests(unittest.TestCase):
    def test_leaves_pin_unchanged_on_python_313(self):
        self.assertEqual(
            resolve_gevent_requirement("gevent==24.11.1", "3.13"),
            "gevent==24.11.1",
        )

    def test_overrides_broken_pin_on_python_314(self):
        self.assertEqual(
            resolve_gevent_requirement("gevent==24.11.1", "3.14"),
            constants.GEVENT_PACKAGE_FOR_PYTHON_314,
        )

    def test_keeps_newer_pin_on_python_314(self):
        self.assertEqual(
            resolve_gevent_requirement("gevent==26.9.0", "3.14"),
            "gevent==26.9.0",
        )


class PatchOdooRequirementsGeventTests(unittest.TestCase):
    def test_patches_matching_marker_line(self):
        line = (
            "gevent==24.11.1 ; sys_platform != 'win32' and python_version >= '3.13'\n"
        )
        with patch(
            "dev_project.bake_venv.evaluate_marker", return_value=True
        ):
            patched = patch_odoo_requirements_gevent_line(line, "3.14")
        self.assertTrue(
            patched.startswith(constants.GEVENT_PACKAGE_FOR_PYTHON_314 + " ;")
        )

    def test_skips_non_matching_marker_line(self):
        line = (
            "gevent==24.2.1 ; sys_platform != 'win32' and python_version < '3.13'\n"
        )
        with patch(
            "dev_project.bake_venv.evaluate_marker", return_value=False
        ):
            self.assertEqual(
                patch_odoo_requirements_gevent_line(line, "3.14"), line
            )

    def test_materialize_writes_temp_file_when_patched(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "requirements.txt"
            src.write_text(
                "gevent==24.11.1 ; python_version >= '3.13'\nBabel==2.17.0\n",
                encoding="utf-8",
            )
            with patch(
                "dev_project.bake_venv.evaluate_marker", return_value=True
            ):
                path, temp_path = materialize_odoo_requirements_path(
                    str(src), "3.14"
                )
            self.assertIsNotNone(temp_path)
            assert temp_path is not None
            try:
                text = Path(path).read_text(encoding="utf-8")
                self.assertIn(constants.GEVENT_PACKAGE_FOR_PYTHON_314, text)
                self.assertNotIn("gevent==24.11.1", text)
                self.assertIn("Babel==2.17.0", text)
            finally:
                os.unlink(temp_path)


class ResolveLibsassRequirementTests(unittest.TestCase):
    def test_leaves_pin_unchanged_on_python_313(self):
        self.assertEqual(
            resolve_libsass_requirement("libsass==0.22.0", "3.13"),
            "libsass==0.22.0",
        )

    def test_overrides_broken_pin_on_python_314(self):
        self.assertEqual(
            resolve_libsass_requirement("libsass==0.22.0", "3.14"),
            constants.LIBSASS_PACKAGE_FOR_PYTHON_314,
        )

    def test_keeps_newer_pin_on_python_314(self):
        self.assertEqual(
            resolve_libsass_requirement("libsass==0.23.0", "3.14"),
            "libsass==0.23.0",
        )


class PatchOdooRequirementsLibsassTests(unittest.TestCase):
    def test_patches_plain_libsass_line(self):
        line = "libsass==0.22.0\n"
        patched = patch_odoo_requirements_libsass_line(line, "3.14")
        self.assertEqual(patched, constants.LIBSASS_PACKAGE_FOR_PYTHON_314 + "\n")

    def test_materialize_rewrites_gevent_and_libsass(self):
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "requirements.txt"
            src.write_text(
                "gevent==24.11.1 ; python_version >= '3.13'\n"
                "libsass==0.22.0\n"
                "Babel==2.17.0\n",
                encoding="utf-8",
            )
            with patch(
                "dev_project.bake_venv.evaluate_marker", return_value=True
            ):
                path, temp_path = materialize_odoo_requirements_path(
                    str(src), "3.14"
                )
            self.assertIsNotNone(temp_path)
            assert temp_path is not None
            try:
                text = Path(path).read_text(encoding="utf-8")
                self.assertIn(constants.GEVENT_PACKAGE_FOR_PYTHON_314, text)
                self.assertIn(constants.LIBSASS_PACKAGE_FOR_PYTHON_314, text)
                self.assertNotIn("libsass==0.22.0", text)
                self.assertIn("Babel==2.17.0", text)
            finally:
                os.unlink(temp_path)


class InstallOdooRequirementGeventOverrideTests(unittest.TestCase):
    @patch("dev_project.bake_venv._run_subprocess")
    def test_install_uses_overridden_gevent_and_patched_requirements(self, mock_run):
        pip = PipRunner(
            base_cmd=["uv"], pip_extra_args=["--link-mode=copy"], cwd="/home/odoo"
        )
        with tempfile.TemporaryDirectory() as tmp:
            src = Path(tmp) / "requirements.txt"
            src.write_text(
                "gevent==24.11.1 ; python_version >= '3.13'\n",
                encoding="utf-8",
            )
            with patch(
                "dev_project.bake_venv.evaluate_marker", return_value=True
            ):
                install_odoo_requirement_packages(
                    ["gevent==24.11.1"],
                    pip,
                    str(src),
                    python_version="3.14",
                )
        install_calls = [call.args[0] for call in mock_run.call_args_list]
        gevent_cmds = [
            cmd
            for cmd in install_calls
            if any(constants.GEVENT_PACKAGE_FOR_PYTHON_314 in part for part in cmd)
        ]
        self.assertTrue(gevent_cmds, msg=f"expected overridden gevent install: {install_calls}")
        req_cmds = [cmd for cmd in install_calls if "-r" in cmd]
        self.assertTrue(req_cmds)
        req_path = req_cmds[0][req_cmds[0].index("-r") + 1]
        self.assertNotEqual(req_path, str(src))


if __name__ == "__main__":
    unittest.main()
