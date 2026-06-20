"""Contract tests for APT repository packaging layout."""

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


class AptRepoPackagingTests(unittest.TestCase):
    def test_public_keyring_present_and_binary(self):
        keyring = PROJECT_ROOT / "packaging" / "apt" / "odpm-archive-keyring.gpg"
        if not keyring.is_file():
            self.skipTest(
                "packaging/apt/odpm-archive-keyring.gpg not committed yet "
                "(gpg --armor --export KEYID | gpg --dearmor > packaging/apt/odpm-archive-keyring.gpg)"
            )
        self.assertGreater(keyring.stat().st_size, 0)
        head = keyring.read_bytes()[:40]
        self.assertNotIn(b"BEGIN PGP", head, msg="keyring must be binary, not armored")
        proc = _list_odpm_keyring(keyring)
        self.assertIn("03040028F53D7AB8", proc.stdout)

    def test_reprepro_distributions_define_stable_and_testing(self):
        distributions = (
            PROJECT_ROOT / "packaging" / "apt" / "reprepro" / "conf" / "distributions"
        ).read_text(encoding="utf-8")
        self.assertIn("Codename: stable", distributions)
        self.assertIn("Codename: testing", distributions)
        self.assertIn("SignWith: %%GPG_KEY_ID%%", distributions)
        self.assertIn("Architectures: amd64 arm64 armhf i386", distributions)
        self.assertNotRegex(distributions, r"(?m)^Architectures: all$")

    def test_package_repo_scripts_exist_and_executable(self):
        for name in (
            "import_apt_signing_key.sh",
            "build_apt_repo.sh",
            "build_yum_repo.sh",
            "preserve_pages_package_repos.sh",
        ):
            script = PROJECT_ROOT / "scripts" / name
            self.assertTrue(script.is_file(), msg=name)
            self.assertTrue(script.stat().st_mode & 0o111, msg=f"{name} not executable")


if __name__ == "__main__":
    unittest.main()
