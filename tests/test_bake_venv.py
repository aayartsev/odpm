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


if __name__ == "__main__":
    unittest.main()
