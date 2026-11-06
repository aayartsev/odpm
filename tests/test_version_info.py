"""Unit tests for ``odpm --version`` git / package metadata enrichment."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from dev_project import constants
from dev_project.host.version_info import (
    format_odpm_version_line,
    read_git_build_meta,
    read_packaged_build_meta,
)
from scripts.write_build_meta import write_build_meta


class VersionInfoTests(unittest.TestCase):
    def test_format_without_meta_is_plain_version(self):
        with patch(
            "dev_project.host.version_info.read_git_build_meta",
            return_value=None,
        ), patch(
            "dev_project.host.version_info.read_packaged_build_meta",
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
        ), patch(
            "dev_project.host.version_info.read_packaged_build_meta",
            return_value=("deadbee", "2020-01-01"),
        ):
            line = format_odpm_version_line("/tmp")
        self.assertEqual(
            line,
            f"{constants.PROJECT_NAME} version: {constants.ODPM_VERSION} "
            "(87564d8, 2026-09-28)",
        )

    def test_format_falls_back_to_packaged_meta(self):
        with patch(
            "dev_project.host.version_info.read_git_build_meta",
            return_value=None,
        ), patch(
            "dev_project.host.version_info.read_packaged_build_meta",
            return_value=("abc1234", "2026-11-05"),
        ):
            line = format_odpm_version_line("/tmp")
        self.assertEqual(
            line,
            f"{constants.PROJECT_NAME} version: {constants.ODPM_VERSION} "
            "(abc1234, 2026-11-05)",
        )

    def test_read_packaged_build_meta_from_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            meta_path = Path(tmp) / "build_meta.json"
            meta_path.write_text(
                json.dumps({"short_sha": "feedfac", "commit_date": "2026-11-01"}),
                encoding="utf-8",
            )
            with patch(
                "dev_project.host.version_info.packaged_build_meta_path",
                return_value=meta_path,
            ):
                meta = read_packaged_build_meta()
        self.assertEqual(meta, ("feedfac", "2026-11-01"))

    def test_write_build_meta_writes_sha_and_date(self):
        repo_root = Path(__file__).resolve().parent.parent
        if not (repo_root / ".git").exists():
            self.skipTest("not a git checkout")
        # write_build_meta needs a real .git; write into the checkout, then clean up.
        out = write_build_meta(repo_root)
        self.addCleanup(lambda: out.unlink(missing_ok=True))
        self.assertTrue(out.is_file())
        payload = json.loads(out.read_text(encoding="utf-8"))
        self.assertRegex(payload["short_sha"], r"^[0-9a-f]+$")
        self.assertRegex(payload["commit_date"], r"^\d{4}-\d{2}-\d{2}$")

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
