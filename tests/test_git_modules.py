import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.git import (
    FILE_SYSTEM_MARKER,
    HandleOdooProjectLink,
)
from dev_project.git.discovery import ProjectDiscovery
from dev_project.git.parser import LinkParser
from dev_project.git.types import OdooProjectData


class LinkParserTests(unittest.TestCase):
    def _bare_link(self):
        link = object.__new__(HandleOdooProjectLink)
        link.project_string = ""
        link.project_link = ""
        link.gitlink = ""
        link.branch = ""
        link.commit = ""
        link.branch_explicit = False
        link.commit_explicit = False
        link.system_type = "standart"
        link.git_regex = r"git@[a-z._-]*:"
        link.start_dir_to_clone = "/tmp/projects"
        link.project_data = OdooProjectData(
            server="",
            author="",
            name="demo",
            git_name="demo",
            commit="",
            branch="",
            relative_path="github.com/acme/demo",
            system_type="standart",
            project_type="project",
            type=constants.GITLINK_TYPE_GIT,
        )
        link.project_path = "/tmp/projects/github.com/acme/demo"
        link.link_type = constants.GITLINK_TYPE_GIT
        return link

    def test_get_git_link_type_detects_file_url(self):
        link = self._bare_link()
        link.project_link = "file:///tmp/my_project"
        self.assertEqual(
            LinkParser(link).get_git_link_type(),
            constants.GITLINK_TYPE_FILE,
        )

    def test_parse_project_string_extracts_branch_and_commit(self):
        link = self._bare_link()
        link.project_string = (
            "https://github.com/acme/demo.git 17.0 deadbeef"
        )
        parser = LinkParser(link)
        parser.parse_project_string()
        self.assertEqual(link.project_link, "https://github.com/acme/demo.git")
        self.assertEqual(link.branch, "17.0")
        self.assertTrue(link.branch_explicit)
        self.assertEqual(link.commit, "deadbeef")
        self.assertTrue(link.commit_explicit)


class ProjectDiscoveryTests(unittest.TestCase):
    def test_get_project_type_module_when_manifest_exists(self):
        with tempfile.TemporaryDirectory() as project_dir:
            module_dir = Path(project_dir) / "my_module"
            module_dir.mkdir()
            (module_dir / "__manifest__.py").write_text("{}", encoding="utf-8")

            link = object.__new__(HandleOdooProjectLink)
            link.project_path = str(module_dir)
            link.project_data = OdooProjectData(
                server="",
                author="",
                name="my_module",
                git_name="my_module",
                commit="",
                branch="",
                relative_path="",
                system_type="standart",
                project_type="project",
                type=constants.GITLINK_TYPE_FILE,
            )

            self.assertEqual(
                ProjectDiscovery(link).get_project_type(),
                constants.TYPE_PROJECT_MODULE,
            )

    def test_apply_inside_docker_path_for_module_doubles_name(self):
        link = object.__new__(HandleOdooProjectLink)
        link.project_path = "/tmp/fake"
        link.project_data = OdooProjectData(
            server="",
            author="",
            name="my_module",
            git_name="my_module",
            commit="",
            branch="",
            relative_path="",
            system_type="standart",
            project_type="project",
            type=constants.GITLINK_TYPE_FILE,
        )
        discovery = ProjectDiscovery(link)

        def fake_get_project_type():
            return constants.TYPE_PROJECT_MODULE

        discovery.get_project_type = fake_get_project_type
        discovery.apply_inside_docker_path()
        self.assertEqual(link.inside_docker_path, "my_module/my_module")


class GitOperationsTests(unittest.TestCase):
    def _operations(self):
        from dev_project.git.operations import GitOperations

        link = object.__new__(HandleOdooProjectLink)
        link.project_path = "/tmp/repo"
        link.gitlink = "https://github.com/acme/demo.git"
        link.project_link = link.gitlink
        link.path_to_ssh_key = ""
        link.project_string = link.gitlink
        return GitOperations(link)

    @patch("dev_project.git.operations.subprocess.run")
    def test_check_repo_url_normalizes_git_suffix(self, mock_run):
        mock_run.return_value = MagicMock(
            stdout="https://github.com/acme/demo.git\n",
            returncode=0,
        )
        ops = self._operations()
        self.assertTrue(
            ops.check_repo_url("/tmp/repo", "https://github.com/acme/demo")
        )
        mock_run.assert_called_once()


class HandleOdooProjectLinkInitTests(unittest.TestCase):
    def test_file_link_sets_cloned_on_build_project(self):
        with tempfile.TemporaryDirectory() as project_dir:
            Path(project_dir, "README").write_text("demo", encoding="utf-8")
            link = HandleOdooProjectLink(
                f"{FILE_SYSTEM_MARKER}{project_dir}",
                "",
                "/tmp/unused",
            )
            link.build_project()
            self.assertTrue(link.is_cloned)
            self.assertEqual(link.project_path, project_dir)


if __name__ == "__main__":
    unittest.main()
