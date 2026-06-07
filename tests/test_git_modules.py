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


class GitRunnerTests(unittest.TestCase):
    def _runner(self, **link_overrides):
        from dev_project.git.runner import GitRunner

        link = object.__new__(HandleOdooProjectLink)
        link.project_path = "/tmp/repo"
        link.path_to_ssh_key = ""
        link.project_string = "https://github.com/acme/demo.git"
        for key, value in link_overrides.items():
            setattr(link, key, value)
        return GitRunner(link)

    def test_build_git_cmd_without_ssh_key(self):
        runner = self._runner()
        self.assertEqual(
            runner.build_git_cmd(["status"]),
            ["git", "status"],
        )

    def test_build_git_cmd_with_ssh_key(self):
        runner = self._runner(path_to_ssh_key="/home/user/.ssh/id_rsa")
        self.assertEqual(
            runner.build_git_cmd(["fetch"]),
            [
                "git",
                "-c",
                "core.sshCommand=ssh -i /home/user/.ssh/id_rsa",
                "fetch",
            ],
        )

    @patch("dev_project.git.runner.run_checked")
    def test_run_git_uses_project_path_as_default_cwd(self, mock_run_checked):
        mock_run_checked.return_value = MagicMock(
            stdout="",
            returncode=0,
            stderr="",
        )
        runner = self._runner()
        runner.run_git(["rev-parse", "HEAD"])
        mock_run_checked.assert_called_once()
        self.assertEqual(mock_run_checked.call_args.kwargs["cwd"], "/tmp/repo")
        self.assertEqual(
            mock_run_checked.call_args.args[0],
            ["git", "rev-parse", "HEAD"],
        )

    @patch("dev_project.git.runner.run_checked")
    def test_run_git_honors_explicit_cwd(self, mock_run_checked):
        mock_run_checked.return_value = MagicMock(
            stdout="",
            returncode=0,
            stderr="",
        )
        runner = self._runner()
        runner.run_git(["remote", "get-url", "origin"], cwd="/other/path")
        self.assertEqual(mock_run_checked.call_args.kwargs["cwd"], "/other/path")


class RepoCloneServiceTests(unittest.TestCase):
    def _service(self, **link_overrides):
        from dev_project.git.clone import RepoCloneService
        from dev_project.git.runner import GitRunner

        link = object.__new__(HandleOdooProjectLink)
        link.project_path = "/tmp/repo"
        link.gitlink = "https://github.com/acme/demo.git"
        link.project_link = link.gitlink
        link.path_to_ssh_key = ""
        link.project_string = link.gitlink
        link.dir_to_clone = "/tmp/clone_base"
        link.system_type = "standart"
        link.link_type = constants.GITLINK_TYPE_GIT
        link.is_cloned = False
        for key, value in link_overrides.items():
            setattr(link, key, value)
        return RepoCloneService(link, GitRunner(link))

    @patch("dev_project.git.runner.run_checked")
    def test_check_repo_url_normalizes_git_suffix(self, mock_run_checked):
        mock_run_checked.return_value = MagicMock(
            stdout="https://github.com/acme/demo.git\n",
            returncode=0,
            stderr="",
        )
        service = self._service()
        self.assertTrue(
            service.check_repo_url("/tmp/repo", "https://github.com/acme/demo")
        )
        mock_run_checked.assert_called_once()

    @patch("dev_project.git.clone.run_logged", return_value=0)
    def test_clone_repo_uses_dir_to_clone_as_cwd(self, mock_run_logged):
        service = self._service()
        service.clone_repo()
        mock_run_logged.assert_called_once()
        self.assertEqual(mock_run_logged.call_args.kwargs["cwd"], "/tmp/clone_base")
        self.assertTrue(service.link.is_cloned)

    @patch("dev_project.git.clone.run_logged", return_value=128)
    def test_clone_repo_raises_git_error_on_failure(self, _mock_run_logged):
        from dev_project.errors import GitError

        service = self._service()
        with self.assertRaises(GitError):
            service.clone_repo()
        self.assertFalse(service.link.is_cloned)

    @patch("dev_project.git.clone.run_logged", return_value=0)
    def test_clone_repo_platform_uses_shallow_depth(self, mock_run_logged):
        service = self._service(
            system_type="platform",
            branch_explicit=True,
            branch="19.0",
            commit_explicit=False,
        )
        service.clone_repo()
        clone_cmd = mock_run_logged.call_args.args[0]
        self.assertIn("--depth", clone_cmd)
        self.assertIn("-b", clone_cmd)
        self.assertIn("19.0", clone_cmd)

    @patch("dev_project.git.clone.RepoCloneService.clone_repo")
    @patch("dev_project.git.clone.os.makedirs")
    @patch("dev_project.git.clone.os.path.exists", return_value=False)
    def test_check_project_does_not_chdir(self, _mock_exists, _mock_makedirs, mock_clone):
        service = self._service()
        with patch("dev_project.git.clone.os.chdir") as mock_chdir:
            service.check_project()
        mock_chdir.assert_not_called()
        mock_clone.assert_called_once()


class CheckoutServiceTests(unittest.TestCase):
    def _service(self, **link_overrides):
        from dev_project.git.checkout import CheckoutService
        from dev_project.git.runner import GitRunner

        link = object.__new__(HandleOdooProjectLink)
        link.project_path = "/tmp/repo"
        link.gitlink = "https://github.com/acme/demo.git"
        link.project_link = link.gitlink
        link.path_to_ssh_key = ""
        link.project_string = link.gitlink
        link.dir_to_clone = "/tmp/clone_base"
        link.system_type = "standart"
        link.link_type = constants.GITLINK_TYPE_GIT
        link.branch = ""
        link.commit = ""
        link.branch_explicit = False
        link.commit_explicit = False
        for key, value in link_overrides.items():
            setattr(link, key, value)
        return CheckoutService(link, GitRunner(link))

    @patch("dev_project.git.checkout.CheckoutService._git_pull")
    @patch("dev_project.git.checkout.CheckoutService.checkout_parsed_or_version")
    def test_checkout_skips_pull_when_commit_explicit(self, mock_parsed, mock_pull):
        service = self._service(commit_explicit=True, commit="deadbeef")
        service.checkout("19.0", update=True, odoo_version_sync=True)
        mock_pull.assert_not_called()
        mock_parsed.assert_called_once_with("19.0")

    @patch("dev_project.git.checkout.CheckoutService.checkout")
    def test_switch_to_branch_uses_hard_checkout(self, mock_checkout):
        service = self._service()
        service.switch_to_branch("18.0")
        mock_checkout.assert_called_once_with("18.0", hard=True)

    @patch("dev_project.git.checkout.CheckoutService.checkout")
    def test_checkout_repository_enables_version_sync(self, mock_checkout):
        service = self._service()
        service.checkout_repository(
            "19.0",
            clean_git_repos=True,
            update_git_repos=True,
        )
        mock_checkout.assert_called_once_with(
            "19.0",
            clean=True,
            update=True,
            odoo_version="19.0",
            odoo_version_sync=True,
        )

    @patch("dev_project.git.runner.run_checked")
    def test_ensure_branch_exists_skips_fetch_when_local_branch_present(
        self, mock_run_checked
    ):
        mock_run_checked.return_value = MagicMock(
            stdout="  19.0\n",
            returncode=0,
            stderr="",
        )
        service = self._service()
        service.ensure_branch_exists("19.0", "19.0")
        mock_run_checked.assert_called_once()
        self.assertEqual(mock_run_checked.call_args.args[0], ["git", "branch"])

    @patch("dev_project.git.runner.run_checked")
    def test_checkout_parsed_or_version_fetches_explicit_commit(self, mock_run_checked):
        mock_run_checked.side_effect = [
            MagicMock(stdout="", returncode=1, stderr=""),
            MagicMock(stdout="", returncode=0, stderr=""),
            MagicMock(stdout="", returncode=0, stderr=""),
        ]
        service = self._service(commit_explicit=True, commit="deadbeef")
        with patch("dev_project.git.checkout.os.path.exists", return_value=True):
            service.checkout_parsed_or_version("19.0")
        self.assertEqual(mock_run_checked.call_count, 3)
        fetch_call = mock_run_checked.call_args_list[1]
        self.assertIn("fetch", fetch_call.args[0])
        self.assertIn("deadbeef", fetch_call.args[0])


class GitOperationsTests(unittest.TestCase):
    def _operations(self, **link_overrides):
        from dev_project.git.operations import GitOperations

        link = object.__new__(HandleOdooProjectLink)
        link.project_path = "/tmp/repo"
        link.gitlink = "https://github.com/acme/demo.git"
        link.project_link = link.gitlink
        link.path_to_ssh_key = ""
        link.project_string = link.gitlink
        link.dir_to_clone = "/tmp/clone_base"
        link.system_type = "standart"
        link.link_type = constants.GITLINK_TYPE_GIT
        for key, value in link_overrides.items():
            setattr(link, key, value)
        return GitOperations(link)

    @patch("dev_project.git.runner.run_checked")
    def test_resolve_head_sha_returns_rev_parse_head(self, mock_run_checked):
        mock_run_checked.return_value = MagicMock(
            stdout="abc123def456\n",
            returncode=0,
            stderr="",
        )
        ops = self._operations()
        with patch("dev_project.git.operations.os.path.exists", return_value=True):
            self.assertEqual(ops.resolve_head_sha(), "abc123def456")

    @patch("dev_project.git.checkout.CheckoutService.checkout")
    def test_checkout_delegates_to_checkout_service(self, mock_checkout):
        ops = self._operations()
        ops.checkout("19.0", update=True, odoo_version_sync=True)
        mock_checkout.assert_called_once_with(
            "19.0",
            commit=None,
            hard=False,
            clean=False,
            update=True,
            odoo_version=None,
            odoo_version_sync=True,
        )

    @patch("dev_project.git.clone.RepoCloneService.check_repo_url", return_value=True)
    def test_check_project_delegates_to_clone_service(self, mock_check_url):
        ops = self._operations()
        with patch("dev_project.git.clone.os.path.exists", return_value=True):
            with patch(
                "dev_project.git.runner.run_checked",
                return_value=MagicMock(stdout="true\n", returncode=0, stderr=""),
            ):
                ops.check_project()
        mock_check_url.assert_called_once()
        self.assertTrue(ops.link.is_cloned)


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
