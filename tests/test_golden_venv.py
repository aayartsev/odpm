"""Unit tests for golden core venv helpers."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.bake_venv import VenvInstallSpec
from dev_project.golden_venv import (
    clone_golden_to_project,
    golden_enabled,
    golden_exists,
    golden_path,
    host_golden_mounts,
    materialize_golden,
    populate_golden_from_project,
    resolve_golden_root_for_host,
)


class GoldenEnabledTests(unittest.TestCase):
    def test_default_enabled(self):
        self.assertTrue(golden_enabled({}))

    def test_disabled_by_zero(self):
        self.assertFalse(golden_enabled({constants.ODPM_GOLDEN_VENV_ENV: "0"}))


class GoldenPathTests(unittest.TestCase):
    def test_resolve_host_root_default(self):
        root = resolve_golden_root_for_host({})
        self.assertEqual(
            root,
            os.path.join(
                os.path.expanduser("~"),
                constants.CONFIG_DIR_IN_HOME_DIR,
                constants.DEFAULT_GOLDEN_VENV_DIRNAME,
            ),
        )

    def test_custom_root(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = resolve_golden_root_for_host(
                {constants.ODPM_GOLDEN_VENV_ROOT_ENV: tmp}
            )
            self.assertEqual(root, os.path.abspath(tmp))
            self.assertEqual(
                golden_path("abc123", root=root),
                os.path.join(root, "abc123"),
            )

    def test_golden_exists_requires_lock_match(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = golden_path("hash-a", root=tmp)
            venv = Path(path) / constants.GOLDEN_VENV_DIR_NAME
            venv.mkdir(parents=True)
            (Path(path) / constants.GOLDEN_LOCK_BASENAME).write_text(
                "hash-a\n", encoding="utf-8"
            )
            self.assertTrue(golden_exists("hash-a", root=tmp))
            self.assertFalse(golden_exists("other", root=tmp))

    def test_golden_exists_false_while_incomplete(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = golden_path("hash-a", root=tmp)
            venv = Path(path) / constants.GOLDEN_VENV_DIR_NAME
            venv.mkdir(parents=True)
            (Path(path) / constants.GOLDEN_LOCK_BASENAME).write_text(
                "hash-a\n", encoding="utf-8"
            )
            (Path(path) / constants.GOLDEN_INCOMPLETE_BASENAME).write_text(
                "1\n", encoding="utf-8"
            )
            self.assertFalse(golden_exists("hash-a", root=tmp))


class HostGoldenMountsTests(unittest.TestCase):
    def test_mounts_root_to_container_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            mounts = host_golden_mounts(cache_root=tmp)
            self.assertEqual(len(mounts), 1)
            self.assertEqual(mounts[0].local, tmp)
            self.assertEqual(
                mounts[0].docker, constants.GOLDEN_VENV_CONTAINER_ROOT
            )


class MaterializeAndCloneTests(unittest.TestCase):
    def _spec(self, project_dir: str, venv_dir: str) -> VenvInstallSpec:
        req = Path(project_dir) / "odoo" / "requirements.txt"
        req.parent.mkdir(parents=True, exist_ok=True)
        req.write_text("wheel\n", encoding="utf-8")
        return VenvInstallSpec(
            project_dir=project_dir,
            venv_dir=venv_dir,
            odoo_requirements_path=str(req),
            extra_packages=[],
            python_version="3.12",
        )

    @patch("dev_project.bake_venv.install_core_fresh")
    @patch("dev_project.golden_venv.write_core_freeze")
    def test_materialize_golden_installs_core(self, mock_freeze, mock_core):
        with tempfile.TemporaryDirectory() as tmp:
            project = os.path.join(tmp, "project")
            os.makedirs(project)
            spec = self._spec(project, os.path.join(project, ".venv"))
            golden_root = os.path.join(tmp, "golden")

            def _fake_install(g_spec, **kwargs):
                os.makedirs(g_spec.venv_dir, exist_ok=True)
                self.assertIsNone(kwargs.get("lock_file_path"))

            mock_core.side_effect = _fake_install
            path = materialize_golden(
                spec, "lock-1", root=golden_root, use_uv=False
            )
            self.assertTrue(golden_exists("lock-1", root=golden_root))
            self.assertFalse(
                os.path.isfile(
                    os.path.join(
                        path, constants.GOLDEN_INCOMPLETE_BASENAME
                    )
                )
            )
            self.assertEqual(path, golden_path("lock-1", root=golden_root))
            mock_freeze.assert_called_once()

    @patch("dev_project.bake_venv.run_pip_command")
    @patch("dev_project.bake_venv.create_venv")
    def test_install_from_freeze_installs_gevent_first(self, mock_create, mock_pip):
        from dev_project.golden_venv import _install_from_freeze

        with tempfile.TemporaryDirectory() as tmp:
            freeze = os.path.join(tmp, "freeze.txt")
            Path(freeze).write_text(
                "gevent==24.2.1\nwheel==0.43.0\n", encoding="utf-8"
            )
            venv_dir = os.path.join(tmp, ".venv")
            ok = _install_from_freeze(
                freeze_path=freeze,
                project_dir=tmp,
                venv_dir=venv_dir,
                python_version="3.12",
                use_uv=True,
            )
            self.assertTrue(ok)
            mock_create.assert_called_once()
            self.assertGreaterEqual(mock_pip.call_count, 2)
            first_cmd = mock_pip.call_args_list[0].args[0]
            self.assertIn("gevent==24.2.1", first_cmd)
            self.assertIn("--no-build-isolation", first_cmd)
            last_cmd = mock_pip.call_args_list[-1].args[0]
            self.assertIn("-r", last_cmd)
    @patch("dev_project.golden_venv._install_from_freeze", return_value=True)
    @patch("dev_project.golden_venv._try_clonevirtualenv", return_value=False)
    def test_clone_falls_back_to_freeze(self, mock_clone, mock_freeze):
        with tempfile.TemporaryDirectory() as tmp:
            golden_dir = os.path.join(tmp, "g")
            src = Path(golden_dir) / constants.GOLDEN_VENV_DIR_NAME
            src.mkdir(parents=True)
            (Path(golden_dir) / constants.GOLDEN_CORE_FREEZE_BASENAME).write_text(
                "wheel==0.1\n", encoding="utf-8"
            )
            dest = os.path.join(tmp, "project", ".venv")
            ok = clone_golden_to_project(
                golden_dir,
                dest,
                python_version="3.12",
                project_dir=os.path.join(tmp, "project"),
                use_uv=True,
            )
            self.assertTrue(ok)
            mock_clone.assert_called_once()
            mock_freeze.assert_called_once()

    @patch("dev_project.golden_venv._install_from_freeze", return_value=True)
    @patch("dev_project.golden_venv.write_core_freeze")
    @patch("dev_project.golden_venv._try_clonevirtualenv")
    def test_populate_from_project_with_clone(
        self, mock_clone, mock_freeze, _mock_install
    ):
        def _clone(src, dest):
            os.makedirs(dest, exist_ok=True)
            return True

        mock_clone.side_effect = _clone
        with tempfile.TemporaryDirectory() as tmp:
            project_venv = os.path.join(tmp, "project", ".venv")
            os.makedirs(project_venv)
            root = os.path.join(tmp, "golden")
            path = populate_golden_from_project(
                project_venv,
                "lock-2",
                root=root,
                python_version="3.12",
                project_dir=os.path.join(tmp, "project"),
                use_uv=False,
            )
            self.assertIsNotNone(path)
            self.assertTrue(golden_exists("lock-2", root=root))
            mock_clone.assert_called_once()
            mock_freeze.assert_called_once()


class PopulateLockTests(unittest.TestCase):
    @patch("dev_project.bake_venv.install_core_fresh")
    @patch("dev_project.golden_venv.write_core_freeze")
    def test_second_materialize_is_noop_when_exists(self, mock_freeze, mock_core):
        with tempfile.TemporaryDirectory() as tmp:
            project = os.path.join(tmp, "project")
            os.makedirs(project)
            spec = VenvInstallSpec(
                project_dir=project,
                venv_dir=os.path.join(project, ".venv"),
                odoo_requirements_path=os.path.join(
                    project, "odoo", "requirements.txt"
                ),
                extra_packages=[],
                python_version="3.12",
            )
            Path(spec.odoo_requirements_path).parent.mkdir(parents=True)
            Path(spec.odoo_requirements_path).write_text("", encoding="utf-8")
            golden_root = os.path.join(tmp, "golden")

            def _fake_install(g_spec, **kwargs):
                os.makedirs(g_spec.venv_dir, exist_ok=True)

            mock_core.side_effect = _fake_install
            materialize_golden(spec, "same", root=golden_root, use_uv=False)
            materialize_golden(spec, "same", root=golden_root, use_uv=False)
            self.assertEqual(mock_core.call_count, 1)


if __name__ == "__main__":
    unittest.main()
