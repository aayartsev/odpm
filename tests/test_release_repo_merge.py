"""Tests for incremental APT/YUM repo merge on GitHub Pages."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ReleaseRepoMergeTests(unittest.TestCase):
    def test_fetch_pages_repo_script_exists_and_executable(self):
        script = PROJECT_ROOT / "scripts" / "fetch_pages_repo.sh"
        self.assertTrue(script.is_file())
        self.assertTrue(script.stat().st_mode & 0o111)

    def test_overlay_pages_repo_script_exists_and_executable(self):
        script = PROJECT_ROOT / "scripts" / "overlay_pages_repo.sh"
        self.assertTrue(script.is_file())
        self.assertTrue(script.stat().st_mode & 0o111)

    def test_build_apt_repo_documents_merge_flag(self):
        script = (PROJECT_ROOT / "scripts" / "build_apt_repo.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("--merge", script)
        self.assertIn("preserved other suites", script)
        self.assertIn("rsync -a", script)

    def test_build_yum_repo_documents_merge_flag(self):
        script = (PROJECT_ROOT / "scripts" / "build_yum_repo.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("--merge", script)
        self.assertIn("build_yum_repo.sh [--merge] SUITE OUT RPM [RPM...]", script)
        self.assertIn("preserving existing suites", script)

    def test_overlay_apt_preserves_other_suite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "site" / "apt"
            source = root / "artifact"
            stable_release = target / "dists" / "stable" / "Release"
            stable_release.parent.mkdir(parents=True)
            stable_release.write_text("Codename: stable\n", encoding="utf-8")
            (target / "pool" / "main" / "o" / "odpm").mkdir(parents=True)
            (target / "pool" / "main" / "o" / "odpm" / "odpm_4.3.0_amd64.deb").write_bytes(
                b"stable-deb"
            )

            testing_release = source / "dists" / "testing" / "Release"
            testing_release.parent.mkdir(parents=True)
            testing_release.write_text("Codename: testing\n", encoding="utf-8")
            (source / "pool" / "main" / "o" / "odpm").mkdir(parents=True)
            (source / "pool" / "main" / "o" / "odpm" / "odpm_4.4.2-beta_amd64.deb").write_bytes(
                b"testing-deb"
            )
            (source / "odpm-archive-keyring.gpg").write_bytes(b"\x99gpg")

            subprocess.run(
                [
                    str(PROJECT_ROOT / "scripts" / "overlay_pages_repo.sh"),
                    "apt",
                    str(target),
                    str(source),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertTrue(stable_release.is_file())
            self.assertTrue((target / "dists" / "testing" / "Release").is_file())
            self.assertTrue(
                (target / "pool" / "main" / "o" / "odpm" / "odpm_4.3.0_amd64.deb").is_file()
            )
            self.assertTrue(
                (
                    target / "pool" / "main" / "o" / "odpm" / "odpm_4.4.2-beta_amd64.deb"
                ).is_file()
            )
            self.assertTrue((target / "odpm-archive-keyring.gpg").is_file())

    def test_overlay_yum_preserves_other_suite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            target = root / "site" / "yum"
            source = root / "artifact"
            (target / "stable" / "repodata").mkdir(parents=True)
            (target / "stable" / "repodata" / "repomd.xml").write_text(
                "<repomd/>", encoding="utf-8"
            )

            (source / "testing" / "repodata").mkdir(parents=True)
            (source / "testing" / "repodata" / "repomd.xml").write_text(
                "<repomd/>", encoding="utf-8"
            )
            (source / "odpm-archive-keyring.asc").write_text(
                "-----BEGIN PGP PUBLIC KEY BLOCK-----\n", encoding="utf-8"
            )

            subprocess.run(
                [
                    str(PROJECT_ROOT / "scripts" / "overlay_pages_repo.sh"),
                    "yum",
                    str(target),
                    str(source),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            self.assertTrue((target / "stable" / "repodata" / "repomd.xml").is_file())
            self.assertTrue((target / "testing" / "repodata" / "repomd.xml").is_file())
            self.assertTrue((target / "odpm-archive-keyring.asc").is_file())

    def test_fetch_pages_repo_exits_zero_when_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "apt-out"
            proc = subprocess.run(
                [
                    str(PROJECT_ROOT / "scripts" / "fetch_pages_repo.sh"),
                    "apt",
                    str(out),
                ],
                check=False,
                capture_output=True,
                text=True,
                env={
                    **os.environ,
                    "PAGES_REPO_BASE": "https://invalid.example.invalid/odpm",
                },
            )
            self.assertEqual(proc.returncode, 0)
            self.assertIn("No live apt repo", proc.stdout)


if __name__ == "__main__":
    unittest.main()
