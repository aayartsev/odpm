import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.bake_venv import (
    PipRunner,
    VenvInstallSpec,
    _make_pip_runner,
    activate_venv,
    apply_venv_env,
    create_venv,
    install_fresh,
    main,
    run_pip_command,
)
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
    @patch("dev_project.bake_venv._run_subprocess_tee_stderr", return_value=(0, ""))
    def test_run_pip_command_uses_argv_without_shell(self, mock_tee):
        run_pip_command("python3 -m pip install wheel", cwd="/tmp/project")

        mock_tee.assert_called_once()
        cmd, kwargs = mock_tee.call_args
        self.assertEqual(
            cmd[0],
            ["python3", "-m", "pip", "install", "wheel"],
        )
        self.assertEqual(kwargs["cwd"], "/tmp/project")

    @patch(
        "dev_project.bake_venv._run_subprocess_tee_stderr",
        return_value=(17, "boom"),
    )
    def test_run_pip_command_failure_raises_venv_error(self, _mock_tee):
        with self.assertRaises(VenvError) as ctx:
            run_pip_command("uv pip install requests --link-mode=copy", cwd="/tmp")

        self.assertEqual(ctx.exception.exit_code, 17)

    @patch("dev_project.bake_venv._run_subprocess")
    @patch("dev_project.bake_venv.apply_venv_env")
    def test_run_pip_command_passes_python_version(self, mock_apply, mock_run):
        run_pip_command(
            ["uv", "pip", "install", "x"],
            cwd="/tmp/project",
            venv_dir="/tmp/project/.venv",
            python_version="3.12",
        )
        mock_apply.assert_called_once_with(
            "/tmp/project/.venv", python_version="3.12"
        )
        self.assertEqual(mock_run.call_args.kwargs.get("python_version"), "3.12")


class PipRunnerTests(unittest.TestCase):
    @patch("dev_project.bake_venv._run_subprocess")
    def test_install_odoo_requirement_packages_installs_implicit_packages(self, mock_run):
        pip = PipRunner(base_cmd=["uv"], pip_extra_args=["--link-mode=hardlink"], cwd="/home/odoo")
        from dev_project.bake_venv import install_odoo_requirement_packages

        install_odoo_requirement_packages(["wheel"], pip, "/home/odoo/requirements.txt")
        mock_run.assert_called()
        install_calls = [call.args[0] for call in mock_run.call_args_list]
        self.assertTrue(
            any("decorator" in cmd for cmd in install_calls),
            msg=f"expected implicit decorator install, got: {install_calls}",
        )

    @patch("dev_project.bake_venv._run_subprocess")
    def test_install_builds_list_argv(self, mock_run):
        pip = PipRunner(base_cmd=["uv"], pip_extra_args=["--link-mode=hardlink"], cwd="/home/odoo")
        pip.install("setuptools", "wheel")
        mock_run.assert_called_once_with(
            ["uv", "pip", "install", "--link-mode=hardlink", "setuptools", "wheel"],
            cwd="/home/odoo",
        )

    def test_make_pip_runner_uv_targets_venv_python(self):
        spec = _spec(venv_dir="/home/odoo/.venv")
        runner = _make_pip_runner(spec, use_uv=True)
        self.assertEqual(
            runner.pip_extra_args,
            ["--link-mode=hardlink", "--python", "/home/odoo/.venv/bin/python3"],
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

    def test_apply_venv_env_sets_wheel_cache_when_python_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            venv_dir = os.path.join(tmp, ".venv")
            bin_dir = os.path.join(venv_dir, "bin")
            os.makedirs(bin_dir)
            Path(os.path.join(bin_dir, "python3")).touch()
            cache_root = os.path.join(tmp, "cache")
            with patch.dict(
                os.environ,
                {constants.ODPM_WHEEL_CACHE_ROOT_ENV: cache_root},
                clear=False,
            ):
                os.environ.pop(constants.PIP_CACHE_DIR_ENV, None)
                os.environ.pop(constants.UV_CACHE_DIR_ENV, None)
                with patch(
                    "dev_project.wheel_cache.use_container_cache_layout",
                    return_value=False,
                ):
                    apply_venv_env(venv_dir, python_version="3.12")
                self.assertEqual(
                    os.environ[constants.PIP_CACHE_DIR_ENV],
                    os.path.join(cache_root, "wheels", "3.12"),
                )
                self.assertEqual(
                    os.environ[constants.UV_CACHE_DIR_ENV],
                    os.path.join(cache_root, "uv"),
                )


def _popen_with_stderr(returncode: int, stderr_text: str = ""):
    """Build a Popen-like mock for ``_run_subprocess_tee_stderr``."""
    from io import StringIO

    buf = StringIO(stderr_text)
    finished = {"done": False}

    def readline():
        line = buf.readline()
        if line == "":
            finished["done"] = True
        return line

    proc = MagicMock()
    proc.stderr = MagicMock()
    proc.stderr.readline = readline
    proc.stderr.read = buf.read
    proc.poll = lambda: returncode if finished["done"] else None
    proc.wait = MagicMock(return_value=returncode)
    proc.returncode = returncode
    return proc


class RunSubprocessEnvTests(unittest.TestCase):
    @patch("dev_project.bake_venv.subprocess.Popen")
    def test_run_subprocess_passes_environ(self, mock_popen):
        mock_popen.return_value = _popen_with_stderr(0)
        from dev_project.bake_venv import _run_subprocess

        with tempfile.TemporaryDirectory() as tmp:
            with patch.dict(
                os.environ,
                {constants.ODPM_WHEEL_CACHE_ROOT_ENV: tmp},
                clear=False,
            ):
                os.environ.pop(constants.PIP_CACHE_DIR_ENV, None)
                os.environ.pop(constants.UV_CACHE_DIR_ENV, None)
                with patch(
                    "dev_project.wheel_cache.use_container_cache_layout",
                    return_value=False,
                ):
                    _run_subprocess(
                        ["true"], cwd=tmp, python_version="3.12"
                    )
        mock_popen.assert_called_once()
        _args, kwargs = mock_popen.call_args
        self.assertIs(kwargs["env"], os.environ)
        self.assertIn(constants.PIP_CACHE_DIR_ENV, os.environ)
        self.assertIs(kwargs["stderr"], __import__("subprocess").PIPE)

    @patch("dev_project.bake_venv.subprocess.Popen")
    def test_run_subprocess_retries_hardlink_with_copy(self, mock_popen):
        from dev_project.bake_venv import _run_subprocess

        mock_popen.side_effect = [
            _popen_with_stderr(1, "error: Invalid cross-device link (EXDEV)\n"),
            _popen_with_stderr(0),
        ]
        _run_subprocess(
            ["uv", "pip", "install", "--link-mode=hardlink", "wheel"],
            cwd="/tmp",
        )
        self.assertEqual(mock_popen.call_count, 2)
        retry_cmd = mock_popen.call_args_list[1].args[0]
        self.assertIn("--link-mode=copy", retry_cmd)
        self.assertNotIn("--link-mode=hardlink", retry_cmd)

    @patch("dev_project.bake_venv.subprocess.Popen")
    def test_run_subprocess_does_not_retry_on_unrelated_hardlink_mention(
        self, mock_popen
    ):
        from dev_project.bake_venv import _run_subprocess

        mock_popen.return_value = _popen_with_stderr(
            1,
            "error: No matching distribution for pkg (used --link-mode=hardlink)\n",
        )
        with self.assertRaises(VenvError):
            _run_subprocess(
                ["uv", "pip", "install", "--link-mode=hardlink", "pkg"],
                cwd="/tmp",
            )
        self.assertEqual(mock_popen.call_count, 1)

    @patch("dev_project.bake_venv.subprocess.Popen")
    def test_run_subprocess_tees_stderr(self, mock_popen):
        from dev_project.bake_venv import _run_subprocess_tee_stderr
        from io import StringIO

        mock_popen.return_value = _popen_with_stderr(0, "downloading wheel\n")
        stderr_buf = StringIO()
        with patch("dev_project.bake_venv.sys.stderr", stderr_buf):
            code, captured = _run_subprocess_tee_stderr(["true"], cwd="/tmp")
        self.assertEqual(code, 0)
        self.assertIn("downloading wheel", captured)
        self.assertIn("downloading wheel", stderr_buf.getvalue())


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

    @patch("dev_project.bake_venv.install_extra_packages")
    @patch("dev_project.bake_venv.install_core_fresh")
    def test_install_fresh_calls_core_then_extras(self, mock_core, mock_extras):
        spec = _spec(extra_packages=["debugpy"])
        install_fresh(spec, use_uv=False)
        mock_core.assert_called_once()
        mock_extras.assert_called_once()
        self.assertEqual(mock_extras.call_args.args[0], ["debugpy"])

    @patch("dev_project.bake_venv.install_extra_packages")
    @patch("dev_project.bake_venv.install_odoo_requirement_packages")
    @patch("dev_project.bake_venv.bootstrap_packages")
    @patch("dev_project.bake_venv.parse_odoo_requirements", return_value=["wheel"])
    @patch("dev_project.bake_venv.activate_venv")
    @patch("dev_project.bake_venv.create_venv")
    def test_install_core_fresh_skips_extras(
        self,
        _mock_create,
        _mock_activate,
        _mock_parse,
        _mock_bootstrap,
        _mock_odoo_reqs,
        mock_extras,
    ):
        from dev_project.bake_venv import install_core_fresh

        with tempfile.TemporaryDirectory() as project_dir:
            odoo_dir = Path(project_dir) / "odoo"
            odoo_dir.mkdir()
            (odoo_dir / "requirements.txt").write_text("", encoding="utf-8")
            lock_path = Path(project_dir) / ".venv" / ".lock"
            lock_path.parent.mkdir()
            spec = _spec(
                project_dir=project_dir,
                venv_dir=str(lock_path.parent),
                odoo_requirements_path=str(odoo_dir / "requirements.txt"),
                extra_packages=["should-not-install"],
            )
            install_core_fresh(
                spec, use_uv=False, lock_file_path=str(lock_path), lock_hash="abc"
            )
            self.assertEqual(lock_path.read_text(encoding="utf-8"), "abc")
        mock_extras.assert_not_called()


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
            env=os.environ,
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


if __name__ == "__main__":
    unittest.main()
