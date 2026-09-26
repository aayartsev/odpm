"""Tests for git module diff and odpm modules CLI."""

from __future__ import annotations

import json
import os
import shlex
import subprocess
import tempfile
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.errors import ConfigError
from dev_project.git.module_diff import (
    ModuleDiffResult,
    classify_modules_from_diff,
    ensure_deploy_gitignore,
    format_module_diff,
    read_last_applied,
    resolve_diff_base,
    write_last_applied,
)
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.host.cli.parse_args import parse_cli_args
from dev_project.modules.commands import run_modules_command
from dev_project.plan.cli import is_modules_mode
from dev_project.system_check_policy import cli_allows_ci_explicit_mode


def _run_git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _init_repo(repo: Path) -> None:
    repo.mkdir(parents=True, exist_ok=True)
    _run_git(repo, "init")
    _run_git(repo, "config", "user.email", "test@example.com")
    _run_git(repo, "config", "user.name", "Test")


def _write_module(repo: Path, tech: str, body: str = "ok") -> None:
    mod = repo / tech
    mod.mkdir(parents=True, exist_ok=True)
    (mod / "__manifest__.py").write_text(
        f"{{'name': '{tech}', 'version': '1.0'}}\n",
        encoding="utf-8",
    )
    (mod / "models.py").write_text(f"# {body}\n", encoding="utf-8")


class ModuleDiffClassifyTests(unittest.TestCase):
    def test_new_module_is_init(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _write_module(repo, "existing")
            _run_git(repo, "add", ".")
            _run_git(repo, "commit", "-m", "base")
            base = _run_git(repo, "rev-parse", "HEAD")

            _write_module(repo, "brand_new")
            _run_git(repo, "add", ".")
            _run_git(repo, "commit", "-m", "add module")

            result = classify_modules_from_diff(str(repo), base=base)
            self.assertEqual(result.init_modules, "brand_new")
            self.assertEqual(result.update_modules, "")

    def test_changed_module_is_update(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _write_module(repo, "sale")
            _run_git(repo, "add", ".")
            _run_git(repo, "commit", "-m", "base")
            base = _run_git(repo, "rev-parse", "HEAD")

            (repo / "sale" / "models.py").write_text("# changed\n", encoding="utf-8")
            _run_git(repo, "add", ".")
            _run_git(repo, "commit", "-m", "change")

            result = classify_modules_from_diff(str(repo), base=base)
            self.assertEqual(result.init_modules, "")
            self.assertEqual(result.update_modules, "sale")

    def test_rename_module_is_init_at_new_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _write_module(repo, "old_mod")
            _run_git(repo, "add", ".")
            _run_git(repo, "commit", "-m", "base")
            base = _run_git(repo, "rev-parse", "HEAD")

            _run_git(repo, "mv", "old_mod", "new_mod")
            _run_git(repo, "commit", "-m", "rename")

            result = classify_modules_from_diff(str(repo), base=base)
            self.assertEqual(result.init_modules, "new_mod")
            self.assertEqual(result.update_modules, "")

    def test_empty_diff(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _write_module(repo, "sale")
            _run_git(repo, "add", ".")
            _run_git(repo, "commit", "-m", "base")
            base = _run_git(repo, "rev-parse", "HEAD")

            result = classify_modules_from_diff(str(repo), base=base)
            self.assertEqual(result.init_modules, "")
            self.assertEqual(result.update_modules, "")

    def test_missing_base_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp) / "repo"
            _init_repo(repo)
            _write_module(repo, "sale")
            _run_git(repo, "add", ".")
            _run_git(repo, "commit", "-m", "base")
            with self.assertRaises(ConfigError):
                classify_modules_from_diff(
                    str(repo), base="deadbeefdeadbeefdeadbeefdeadbeefdeadbeef"
                )


class ModuleDiffBaselineTests(unittest.TestCase):
    def test_cli_diff_base_wins(self):
        with tempfile.TemporaryDirectory() as project_dir:
            resolved = resolve_diff_base(
                project_dir=project_dir,
                cli_diff_base="abc123",
                environ={
                    constants.ODPM_DIFF_BASE_ENV: "env-sha",
                    constants.CI_MERGE_REQUEST_DIFF_BASE_SHA_ENV: "ci-sha",
                },
            )
            self.assertEqual(resolved, "abc123")

    def test_odpm_diff_base_env(self):
        with tempfile.TemporaryDirectory() as project_dir:
            resolved = resolve_diff_base(
                project_dir=project_dir,
                cli_diff_base=None,
                environ={
                    constants.ODPM_DIFF_BASE_ENV: "env-sha",
                    constants.CI_MERGE_REQUEST_DIFF_BASE_SHA_ENV: "ci-sha",
                },
            )
            self.assertEqual(resolved, "env-sha")

    def test_ci_merge_request_sha(self):
        with tempfile.TemporaryDirectory() as project_dir:
            resolved = resolve_diff_base(
                project_dir=project_dir,
                cli_diff_base=None,
                environ={constants.CI_MERGE_REQUEST_DIFF_BASE_SHA_ENV: "ci-sha"},
            )
            self.assertEqual(resolved, "ci-sha")

    def test_last_applied_sentinel_requires_marker(self):
        with tempfile.TemporaryDirectory() as project_dir:
            with self.assertRaises(ConfigError):
                resolve_diff_base(
                    project_dir=project_dir,
                    cli_diff_base=constants.LAST_APPLIED_SENTINEL,
                    environ={},
                )

    def test_last_applied_from_marker(self):
        with tempfile.TemporaryDirectory() as project_dir:
            write_last_applied(project_dir, "marker-sha")
            resolved = resolve_diff_base(
                project_dir=project_dir,
                cli_diff_base=None,
                environ={},
            )
            self.assertEqual(resolved, "marker-sha")

    def test_no_baseline_raises(self):
        with tempfile.TemporaryDirectory() as project_dir:
            with self.assertRaises(ConfigError):
                resolve_diff_base(
                    project_dir=project_dir,
                    cli_diff_base=None,
                    environ={},
                )


class DeployMarkerTests(unittest.TestCase):
    def test_write_and_read_marker(self):
        with tempfile.TemporaryDirectory() as project_dir:
            path = write_last_applied(project_dir, "deadbeef")
            self.assertTrue(os.path.isfile(path))
            marker = read_last_applied(project_dir)
            assert marker is not None
            self.assertEqual(marker.developing_sha, "deadbeef")
            self.assertTrue(marker.applied_at)

            gitignore = Path(project_dir) / ".odpm" / ".gitignore"
            self.assertTrue(gitignore.is_file())
            self.assertIn("deploy/", gitignore.read_text(encoding="utf-8"))

    def test_ensure_gitignore_idempotent(self):
        with tempfile.TemporaryDirectory() as project_dir:
            odpm = Path(project_dir) / ".odpm"
            odpm.mkdir()
            gitignore = odpm / ".gitignore"
            gitignore.write_text("secrets.json\n", encoding="utf-8")
            ensure_deploy_gitignore(project_dir)
            ensure_deploy_gitignore(project_dir)
            content = gitignore.read_text(encoding="utf-8")
            self.assertEqual(content.count("deploy/"), 1)
            self.assertIn("secrets.json", content)


class ModuleDiffFormatTests(unittest.TestCase):
    def test_shell_format_eval_safe(self):
        result = ModuleDiffResult(
            init_modules="a,b",
            update_modules="c",
            base="base",
            head="head",
        )
        text = format_module_diff(result, "shell")
        self.assertIn("export ODPM_INIT_MODULES=", text)
        self.assertIn("export ODPM_UPDATE_MODULES=", text)
        empty = ModuleDiffResult("", "", "b", "h")
        empty_text = format_module_diff(empty, "shell")
        self.assertIn(f"export ODPM_INIT_MODULES={shlex.quote('')}", empty_text)

    def test_json_format(self):
        result = ModuleDiffResult("a", "b", "base", "head")
        payload = json.loads(format_module_diff(result, "json"))
        self.assertEqual(payload["init_modules"], "a")
        self.assertEqual(payload["update_modules"], "b")


class ModulesCliArgsTests(unittest.TestCase):
    def test_parse_modules_diff(self):
        cli_args = parse_cli_args(["modules", "diff"])
        self.assertEqual(cli_args.command, "modules")
        self.assertEqual(cli_args.modules_subcommand, "diff")
        self.assertEqual(cli_args.modules_diff_format, "text")
        self.assertTrue(is_modules_mode(cli_args))

    def test_parse_modules_diff_options(self):
        cli_args = parse_cli_args(
            ["modules", "diff", "--diff-base", "@last-applied", "--format", "shell"]
        )
        self.assertEqual(cli_args.modules_diff_base, "@last-applied")
        self.assertEqual(cli_args.modules_diff_format, "shell")

    def test_parse_record_applied(self):
        cli_args = parse_cli_args(["modules", "record-applied"])
        self.assertEqual(cli_args.modules_subcommand, "record-applied")

    def test_ci_allowlist_includes_modules(self):
        self.assertTrue(cli_allows_ci_explicit_mode(OdpmCliArgs(command="modules")))
        self.assertTrue(
            cli_allows_ci_explicit_mode(OdpmCliArgs(modules_subcommand="diff"))
        )


class ModulesCommandIntegrationTests(unittest.TestCase):
    def test_diff_and_record_applied(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp) / "project"
            repo = Path(tmp) / "developing"
            project_dir.mkdir()
            _init_repo(repo)
            _write_module(repo, "base_mod")
            _run_git(repo, "add", ".")
            _run_git(repo, "commit", "-m", "base")
            base = _run_git(repo, "rev-parse", "HEAD")

            _write_module(repo, "new_mod")
            (repo / "base_mod" / "models.py").write_text("# upd\n", encoding="utf-8")
            _run_git(repo, "add", ".")
            _run_git(repo, "commit", "-m", "change")

            config = MagicMock()
            config.project_dir = str(project_dir)
            config.developing_project = MagicMock(project_path=str(repo))

            cli_args = OdpmCliArgs(
                command="modules",
                modules_subcommand="diff",
                modules_diff_base=base,
                modules_diff_format="json",
            )
            buf = StringIO()
            with patch("sys.stdout", buf):
                code = run_modules_command(cli_args, config)
            self.assertEqual(code, 0)
            payload = json.loads(buf.getvalue())
            self.assertEqual(payload["init_modules"], "new_mod")
            self.assertEqual(payload["update_modules"], "base_mod")

            record_args = OdpmCliArgs(
                command="modules",
                modules_subcommand="record-applied",
            )
            self.assertEqual(run_modules_command(record_args, config), 0)
            marker = read_last_applied(str(project_dir))
            assert marker is not None
            self.assertEqual(marker.developing_sha, _run_git(repo, "rev-parse", "HEAD"))


if __name__ == "__main__":
    unittest.main()