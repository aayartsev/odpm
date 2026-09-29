"""Unit tests for ``odpm --version`` git metadata enrichment."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from dev_project import constants
from dev_project.host.version_info import (
    format_odpm_version_line,
    read_git_build_meta,
)


class VersionInfoTests(unittest.TestCase):
    def test_format_without_git_is_plain_version(self):
        with patch(
            "dev_project.host.version_info.read_git_build_meta",
            return_value=None,
        ):
            line = format_odpm_version_line("/nonexistent")
        self.assertEqual(
            line,
            f"{constants.PROJECT_NAME} version: {constants.ODPM_VERSION}",
        )

    def test_format_with_git_appends_sha_and_date(self):
        with patch(
            "dev_project.host.version_info.read_git_build_meta",
            return_value=("87564d8", "2026-09-28"),
        ):
            line = format_odpm_version_line("/tmp")
        self.assertEqual(
            line,
            f"{constants.PROJECT_NAME} version: {constants.ODPM_VERSION} "
            "(87564d8, 2026-09-28)",
        )

    def test_read_git_build_meta_from_repo_checkout(self):
        repo_root = Path(__file__).resolve().parent.parent
        if not (repo_root / ".git").exists():
            self.skipTest("not a git checkout")
        meta = read_git_build_meta(str(repo_root))
        self.assertIsNotNone(meta)
        assert meta is not None
        short_sha, commit_date = meta
        self.assertRegex(short_sha, r"^[0-9a-f]+$")
        self.assertRegex(commit_date, r"^\d{4}-\d{2}-\d{2}$")


if __name__ == "__main__":
    unittest.main()
