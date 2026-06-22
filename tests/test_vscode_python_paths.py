"""Tests for Pylance extraPaths generation from Odoo addon roots."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.config.types import SubProject
from dev_project.project_env.services import (
    PythonAnalysisPathsBuilder,
    VscodeConfigurator,
)
from dev_project.symlinks import SymlinksSources


def _make_paths_env(
    *,
    project_dir: str,
    odoo_src_dir: str,
    developing_path: str,
    dependency_paths: list[str] | None = None,
    symlinks_sources: list[SymlinksSources] | None = None,
    catalogs_of_modules_data: list[SubProject] | None = None,
    python_version: str = "3.10",
) -> MagicMock:
    env = MagicMock()
    config = MagicMock()
    config.project_dir = project_dir
    config.dependencies_dir = os.path.join(project_dir, constants.DEPENDENCIES_DIR)
    config.venv_dir = os.path.join(project_dir, constants.VENV_DIR_NAME)
    config.python_version = python_version
    config.odoo_src_dir = odoo_src_dir
    config.symlinks_sources = symlinks_sources or []
    config.dependencies_projects = []
    layout = MagicMock()
    layout.catalogs_of_modules_data = catalogs_of_modules_data or []
    env.host_ctx = MagicMock()
    env.host_ctx.addon_layout = layout

    developing = MagicMock()
    developing.project_path = developing_path
    config.developing_project = developing

    for dep_path in dependency_paths or []:
        dep = MagicMock()
        dep.project_path = dep_path
        config.dependencies_projects.append(dep)

    env.config = config
    return env


class PythonAnalysisPathsBuilderTests(unittest.TestCase):
    def test_build_includes_platform_developing_dependencies_and_venv(self):
        with tempfile.TemporaryDirectory() as project_dir:
            odoo_src = os.path.join(project_dir, "sources", "odoo")
            developing = os.path.join(project_dir, "sources", "app")
            dep_a = os.path.join(project_dir, "sources", "oca-web")
            dep_b = os.path.join(project_dir, "sources", "partner-contact")
            venv_site = os.path.join(
                project_dir,
                constants.VENV_DIR_NAME,
                "lib",
                "python3.10",
                "site-packages",
            )
            for path in (odoo_src, developing, dep_a, dep_b, venv_site):
                os.makedirs(path)

            env = _make_paths_env(
                project_dir=project_dir,
                odoo_src_dir=odoo_src,
                developing_path=developing,
                dependency_paths=[dep_a, dep_b],
            )

            paths = PythonAnalysisPathsBuilder(env).build()

            self.assertIn(
                f"{constants.VENV_DIR_NAME}/lib/python3.10/site-packages",
                paths,
            )
            self.assertIn("sources/odoo", paths)
            self.assertIn("sources/app", paths)
            self.assertIn("sources/oca-web", paths)
            self.assertIn("sources/partner-contact", paths)

    def test_build_prefers_workspace_relative_symlink_paths(self):
        with tempfile.TemporaryDirectory() as project_dir:
            odoo_src = os.path.join(project_dir, "sources", "odoo")
            dep_src = os.path.join(project_dir, "sources", "oca-web")
            os.makedirs(odoo_src)
            os.makedirs(dep_src)
            os.makedirs(os.path.join(project_dir, constants.DEPENDENCIES_DIR))

            odoo_link = os.path.join(project_dir, constants.PLATFORM_NAME)
            os.symlink(odoo_src, odoo_link)
            dep_link = os.path.join(
                project_dir, constants.DEPENDENCIES_DIR, "oca-web"
            )
            os.symlink(dep_src, dep_link)

            env = _make_paths_env(
                project_dir=project_dir,
                odoo_src_dir=odoo_src,
                developing_path=odoo_src,
                dependency_paths=[dep_src],
                symlinks_sources=[
                    SymlinksSources(source_path=odoo_src, link_path=odoo_link),
                    SymlinksSources(source_path=dep_src, link_path=dep_link),
                ],
            )

            paths = PythonAnalysisPathsBuilder(env).build()

            self.assertIn(constants.PLATFORM_NAME, paths)
            self.assertIn(f"{constants.DEPENDENCIES_DIR}/oca-web", paths)
            self.assertNotIn(os.path.realpath(dep_src), paths)

    def test_build_skips_missing_directories(self):
        with tempfile.TemporaryDirectory() as project_dir:
            odoo_src = os.path.join(project_dir, "sources", "odoo")
            os.makedirs(odoo_src)
            missing_dep = os.path.join(project_dir, "sources", "missing")

            env = _make_paths_env(
                project_dir=project_dir,
                odoo_src_dir=odoo_src,
                developing_path=odoo_src,
                dependency_paths=[missing_dep],
            )

            paths = PythonAnalysisPathsBuilder(env).build()

            self.assertEqual(paths, ["sources/odoo"])

    def test_build_includes_subproject_addon_roots(self):
        with tempfile.TemporaryDirectory() as project_dir:
            odoo_src = os.path.join(project_dir, "sources", "odoo")
            repo_root = os.path.join(project_dir, "sources", "mono")
            addon_root = os.path.join(repo_root, "addons")
            os.makedirs(odoo_src)
            os.makedirs(addon_root)

            env = _make_paths_env(
                project_dir=project_dir,
                odoo_src_dir=odoo_src,
                developing_path=repo_root,
                catalogs_of_modules_data=[
                    SubProject(
                        subproject_dir_path=addon_root,
                        subproject_rel_path="addons",
                        list_of_modules=[],
                        list_of_python_packages=[],
                    )
                ],
            )

            paths = PythonAnalysisPathsBuilder(env).build()

            self.assertIn("sources/mono", paths)
            self.assertIn("sources/mono/addons", paths)


class VscodeSettingsExtraPathsTests(unittest.TestCase):
    def test_generate_vscode_settings_json_writes_computed_extra_paths(self):
        program_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        with tempfile.TemporaryDirectory() as project_dir:
            os.makedirs(
                os.path.join(project_dir, constants.PROJECT_SERVICE_DIRECTORY),
                exist_ok=True,
            )
            shutil.copy(
                os.path.join(
                    program_dir,
                    "dev_project",
                    "templates",
                    "vscode_settings.json",
                ),
                os.path.join(
                    project_dir, constants.PROJECT_VSCODE_SETTINGS_TEMPLATE
                ),
            )

            odoo_src = os.path.join(project_dir, "sources", "odoo")
            dep_src = os.path.join(project_dir, "sources", "oca-web")
            os.makedirs(odoo_src)
            os.makedirs(dep_src)
            os.makedirs(os.path.join(project_dir, constants.DEPENDENCIES_DIR))
            dep_link = os.path.join(
                project_dir, constants.DEPENDENCIES_DIR, "oca-web"
            )
            os.symlink(dep_src, dep_link)

            env = _make_paths_env(
                project_dir=project_dir,
                odoo_src_dir=odoo_src,
                developing_path=odoo_src,
                dependency_paths=[dep_src],
                symlinks_sources=[
                    SymlinksSources(source_path=dep_src, link_path=dep_link),
                ],
            )

            VscodeConfigurator(env).generate_vscode_settings_json()

            settings_path = os.path.join(project_dir, ".vscode", "settings.json")
            with open(settings_path, encoding="utf-8") as settings_file:
                payload = json.load(settings_file)

            extra_paths = payload["python.analysis.extraPaths"]
            self.assertEqual(payload["python.autoComplete.extraPaths"], extra_paths)
            self.assertEqual(payload["python.analysis.diagnosticMode"], "workspace")
            self.assertIn(f"{constants.DEPENDENCIES_DIR}/oca-web", extra_paths)
            self.assertIn("sources/odoo", extra_paths)


if __name__ == "__main__":
    unittest.main()
