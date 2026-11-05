"""Unit tests for lint-layer pre-commit bake."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dev_project.bake_pre_commit import (
    BakePreCommitError,
    _BAKE_SUBDIR,
    bake_pre_commit,
    main,
)


class BakePreCommitTests(unittest.TestCase):
    def test_missing_config_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(BakePreCommitError):
                bake_pre_commit(tmp)

    @patch("dev_project.bake_pre_commit.subprocess.run")
    def test_bake_uses_isolated_subdir_and_commits(self, mock_run):
        def _fake_run(argv, cwd=None, check=False):
            # git diff --cached --quiet → 1 means staged changes exist.
            if list(argv)[:3] == ["git", "diff", "--cached"]:
                return type("R", (), {"returncode": 1})()
            return type("R", (), {"returncode": 0})()

        mock_run.side_effect = _fake_run
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".pre-commit-config.yaml").write_text(
                "repos: []\n", encoding="utf-8"
            )
            # Foreign .git in WORKDIR must not be used for bake.
            (root / ".git").mkdir()
            bake_pre_commit(str(root))
            bake_dir = root / _BAKE_SUBDIR
            self.assertTrue((bake_dir / ".pre-commit-config.yaml").is_file())
            expected_cwd = str(bake_dir)
            commands = [
                (list(call.args[0]), call.kwargs.get("cwd"))
                for call in mock_run.call_args_list
            ]

        bake_cwds = {cwd for _, cwd in commands if cwd}
        self.assertEqual(bake_cwds, {expected_cwd})
        argv_only = [argv for argv, _ in commands]
        self.assertEqual(argv_only[0][:2], ["git", "init"])
        self.assertEqual(argv_only[1][:2], ["git", "add"])
        self.assertTrue(any("commit" in argv for argv in argv_only))
        self.assertEqual(argv_only[-1], ["pre-commit", "install-hooks"])

    @patch("dev_project.bake_pre_commit.subprocess.run")
    def test_bake_skips_commit_when_index_unchanged(self, mock_run):
        def _fake_run(argv, cwd=None, check=False):
            if list(argv)[:3] == ["git", "diff", "--cached"]:
                return type("R", (), {"returncode": 0})()
            return type("R", (), {"returncode": 0})()

        mock_run.side_effect = _fake_run
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".pre-commit-config.yaml").write_text(
                "repos: []\n", encoding="utf-8"
            )
            bake_pre_commit(str(root))

        argv_only = [list(call.args[0]) for call in mock_run.call_args_list]
        self.assertFalse(any("commit" in argv for argv in argv_only))
        self.assertEqual(argv_only[-1], ["pre-commit", "install-hooks"])

    @patch("dev_project.bake_pre_commit.subprocess.run")
    def test_bake_adds_hooks_file_when_present(self, mock_run):
        def _fake_run(argv, cwd=None, check=False):
            if list(argv)[:3] == ["git", "diff", "--cached"]:
                return type("R", (), {"returncode": 1})()
            return type("R", (), {"returncode": 0})()

        mock_run.side_effect = _fake_run
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / ".pre-commit-config.yaml").write_text(
                "repos: []\n", encoding="utf-8"
            )
            (root / ".pre-commit-hooks.yaml").write_text(
                "[]\n", encoding="utf-8"
            )
            bake_pre_commit(str(root))
            self.assertTrue(
                (root / _BAKE_SUBDIR / ".pre-commit-hooks.yaml").is_file()
            )
        add_cmd = next(
            list(call.args[0])
            for call in mock_run.call_args_list
            if list(call.args[0])[:2] == ["git", "add"]
        )
        self.assertIn(".pre-commit-hooks.yaml", add_cmd)

    @patch("dev_project.bake_pre_commit.bake_pre_commit")
    def test_main_exits_on_bake_error(self, mock_bake):
        mock_bake.side_effect = BakePreCommitError("boom")
        with self.assertRaises(SystemExit) as ctx:
            main(["--workdir", "/tmp"])
        self.assertEqual(ctx.exception.code, 1)


if __name__ == "__main__":
    unittest.main()
