"""Contract tests for YUM repository packaging layout."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class YumRepoPackagingTests(unittest.TestCase):
    def test_public_keyring_shared_with_apt(self):
        keyring = PROJECT_ROOT / "packaging" / "apt" / "odpm-archive-keyring.gpg"
        if not keyring.is_file():
            self.skipTest("packaging/apt/odpm-archive-keyring.gpg not committed yet")
        self.assertGreater(keyring.stat().st_size, 0)

    def test_repo_templates_define_stable_and_testing(self):
        testing = (PROJECT_ROOT / "packaging" / "yum" / "odpm-testing.repo").read_text(
            encoding="utf-8"
        )
        stable = (PROJECT_ROOT / "packaging" / "yum" / "odpm-stable.repo").read_text(
            encoding="utf-8"
        )
        self.assertIn("baseurl=https://aayartsev.github.io/odpm/yum/testing", testing)
        self.assertIn("baseurl=https://aayartsev.github.io/odpm/yum/stable", stable)
        for content in (testing, stable):
            self.assertIn("gpgcheck=1", content)
            self.assertIn("repo_gpgcheck=1", content)
            self.assertIn(
                "gpgkey=https://aayartsev.github.io/odpm/yum/odpm-archive-keyring.gpg",
                content,
            )

    def test_yum_script_exists_and_executable(self):
        script = PROJECT_ROOT / "scripts" / "build_yum_repo.sh"
        self.assertTrue(script.is_file())
        self.assertTrue(script.stat().st_mode & 0o111)

    def test_public_keyring_lists_odpm_signing_key(self):
        keyring = PROJECT_ROOT / "packaging" / "apt" / "odpm-archive-keyring.gpg"
        if not keyring.is_file():
            self.skipTest("packaging/apt/odpm-archive-keyring.gpg not committed yet")
        proc = subprocess.run(
            [
                "gpg",
                "--no-default-keyring",
                "--keyring",
                str(keyring),
                "--list-keys",
                "--with-colons",
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        self.assertIn("03040028F53D7AB8", proc.stdout)


if __name__ == "__main__":
    unittest.main()
