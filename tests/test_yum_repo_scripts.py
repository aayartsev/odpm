"""Contract tests for YUM repository packaging layout."""

from __future__ import annotations

import os
import subprocess
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _list_odpm_keyring(keyring: Path) -> subprocess.CompletedProcess[str]:
    """List keys from a shipped keyring without the host gpg keyboxd config."""
    with tempfile.TemporaryDirectory() as tmp:
        env = {**os.environ, "GNUPGHOME": tmp}
        return subprocess.run(
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
            env=env,
        )


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
                "gpgkey=https://aayartsev.github.io/odpm/yum/odpm-archive-keyring.asc",
                content,
            )

    def test_armored_key_export_for_rpm(self):
        keyring = PROJECT_ROOT / "packaging" / "apt" / "odpm-archive-keyring.gpg"
        if not keyring.is_file():
            self.skipTest("packaging/apt/odpm-archive-keyring.gpg not committed yet")
        with tempfile.TemporaryDirectory() as gnupg_home:
            env = {**os.environ, "GNUPGHOME": gnupg_home}
            proc = subprocess.run(
                [
                    "gpg",
                    "--no-default-keyring",
                    "--keyring",
                    str(keyring),
                    "--export",
                    "--armor",
                ],
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
            self.assertIn("-----BEGIN PGP PUBLIC KEY BLOCK-----", proc.stdout)
            show = subprocess.run(
                ["gpg", "--import-options", "show-only", "--import"],
                input=proc.stdout,
                check=True,
                capture_output=True,
                text=True,
                env=env,
            )
        self.assertIn("03040028F53D7AB8", show.stdout)

    def test_yum_script_exists_and_executable(self):
        script = PROJECT_ROOT / "scripts" / "build_yum_repo.sh"
        self.assertTrue(script.is_file())
        self.assertTrue(script.stat().st_mode & 0o111)

    def test_yum_script_usage_documents_multi_rpm(self):
        script = (PROJECT_ROOT / "scripts" / "build_yum_repo.sh").read_text(
            encoding="utf-8"
        )
        self.assertIn("build_yum_repo.sh [--merge] SUITE OUT RPM [RPM...]", script)

    def test_public_keyring_lists_odpm_signing_key(self):
        keyring = PROJECT_ROOT / "packaging" / "apt" / "odpm-archive-keyring.gpg"
        if not keyring.is_file():
            self.skipTest("packaging/apt/odpm-archive-keyring.gpg not committed yet")
        proc = _list_odpm_keyring(keyring)
        self.assertIn("03040028F53D7AB8", proc.stdout)


if __name__ == "__main__":
    unittest.main()
