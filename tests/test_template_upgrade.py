import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.project_dir_manager import (
    ProjectDirManager,
    template_needs_upgrade,
)


class TemplateNeedsUpgradeTests(unittest.TestCase):
    def test_missing_template_does_not_need_upgrade(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = os.path.join(tmp_dir, "missing")
            self.assertFalse(
                template_needs_upgrade(path, constants.DOCKERIGNORE_TEMPLATE_MARKERS)
            )

    def test_current_dockerignore_does_not_need_upgrade(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "dockerignore"
            path.write_text(
                "**/.git\n.venv\n.odpm/ci-build-context\n",
                encoding="utf-8",
            )
            self.assertFalse(
                template_needs_upgrade(str(path), constants.DOCKERIGNORE_TEMPLATE_MARKERS)
            )

    def test_legacy_dockerignore_needs_upgrade(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "dockerignore"
            path.write_text("**/.git\n.venv\n", encoding="utf-8")
            self.assertTrue(
                template_needs_upgrade(str(path), constants.DOCKERIGNORE_TEMPLATE_MARKERS)
            )

    def test_current_dockerfile_does_not_need_upgrade(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "dockerfile"
            path.write_text(
                "FROM python:{PYTHON_VERSION}-bookworm\n",
                encoding="utf-8",
            )
            self.assertFalse(
                template_needs_upgrade(str(path), constants.DOCKERFILE_TEMPLATE_MARKERS)
            )

    def test_legacy_dockerfile_needs_upgrade(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "dockerfile"
            path.write_text("FROM python:3.11-bookworm\n", encoding="utf-8")
            self.assertTrue(
                template_needs_upgrade(str(path), constants.DOCKERFILE_TEMPLATE_MARKERS)
            )


class EnsureProjectTemplateTests(unittest.TestCase):
    def _program_dir(self) -> str:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _make_manager(self, project_dir: str) -> ProjectDirManager:
        os.makedirs(
            os.path.join(project_dir, constants.PROJECT_SERVICE_DIRECTORY),
            exist_ok=True,
        )
        return ProjectDirManager(
            project_dir,
            MagicMock(init=False, odoo_git_link=None),
            self._program_dir(),
        )

    def test_rebuild_dockerignore_upgrades_legacy_project_template(self):
        with tempfile.TemporaryDirectory() as project_dir:
            manager = self._make_manager(project_dir)
            project_template = (
                Path(project_dir)
                / constants.PROJECT_DOCKERIGNORE_TEMPLATE_FILE_RELATIVE_PATH
            )
            project_template.parent.mkdir(parents=True, exist_ok=True)
            project_template.write_text("**/.git\n.venv\n", encoding="utf-8")

            manager.rebuild_dockerignore_template()

            content = project_template.read_text(encoding="utf-8")
            self.assertIn(".odpm/ci-build-context", content)

    def test_rebuild_dockerfile_upgrades_legacy_project_template(self):
        with tempfile.TemporaryDirectory() as project_dir:
            manager = self._make_manager(project_dir)
            template_name = "debian_12_dockerfile"
            project_template = Path(project_dir) / constants.PROJECT_SERVICE_DIRECTORY / template_name
            project_template.parent.mkdir(parents=True, exist_ok=True)
            project_template.write_text("FROM python:3.12-bookworm\n", encoding="utf-8")

            manager.rebuild_dockerfile_template(docker_template_filename=template_name)

            content = project_template.read_text(encoding="utf-8")
            self.assertIn("{PYTHON_VERSION}", content)


if __name__ == "__main__":
    unittest.main()
