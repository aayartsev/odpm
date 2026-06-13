"""Contract tests for APT repository packaging layout."""

from __future__ import annotations

import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class AptRepoPackagingTests(unittest.TestCase):
    def test_public_keyring_present(self):
        keyring = PROJECT_ROOT / "packaging" / "apt" / "odpm-archive-keyring.gpg"
        if not keyring.is_file():
            self.skipTest(
                "packaging/apt/odpm-archive-keyring.gpg not committed yet "
                "(gpg --export KEYID > packaging/apt/odpm-archive-keyring.gpg)"
            )
        self.assertGreater(keyring.stat().st_size, 0)

    def test_reprepro_distributions_define_stable_and_testing(self):
        distributions = (
            PROJECT_ROOT / "packaging" / "apt" / "reprepro" / "conf" / "distributions"
        ).read_text(encoding="utf-8")
        self.assertIn("Codename: stable", distributions)
        self.assertIn("Codename: testing", distributions)
        self.assertIn("SignWith: %%GPG_KEY_ID%%", distributions)
        self.assertIn("Architectures: amd64 arm64 armhf i386", distributions)
        self.assertNotRegex(distributions, r"(?m)^Architectures: all$")

    def test_apt_scripts_exist_and_executable(self):
        for name in ("import_apt_signing_key.sh", "build_apt_repo.sh"):
            script = PROJECT_ROOT / "scripts" / name
            self.assertTrue(script.is_file(), msg=name)
            self.assertTrue(script.stat().st_mode & 0o111, msg=f"{name} not executable")


if __name__ == "__main__":
    unittest.main()
