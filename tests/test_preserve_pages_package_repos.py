"""Tests for scripts/preserve_pages_package_repos.sh helpers."""

from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = PROJECT_ROOT / "scripts" / "preserve_pages_package_repos.sh"


def _source_bash_function(function: str, *args: str) -> subprocess.CompletedProcess[str]:
    quoted_args = " ".join(f'"{arg}"' for arg in args)
    return subprocess.run(
        ["bash", "-c", f'source "{SCRIPT}"; {function} {quoted_args}'],
        check=True,
        capture_output=True,
        text=True,
    )


class PreservePagesPackageReposTests(unittest.TestCase):
    def test_apt_paths_from_release_parses_sha256_and_sha512(self):
        release = """Architectures: amd64 all
SHA256:
 abc 123 dists/stable/Release
 def 456 dists/stable/main/binary-amd64/Packages
 ghi 789 pool/main/o/odpm/odpm_4.3.0-1_all.deb
SHA512:
 jkl 111 dists/stable/InRelease
 mno 222 dists/stable/Release.gpg
"""
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as fh:
            fh.write(release)
            release_path = fh.name

        try:
            result = _source_bash_function("apt_paths_from_release", release_path)
        finally:
            Path(release_path).unlink(missing_ok=True)

        paths = [line for line in result.stdout.splitlines() if line.strip()]
        self.assertEqual(
            set(paths),
            {
                "dists/stable/Release",
                "dists/stable/main/binary-amd64/Packages",
                "pool/main/o/odpm/odpm_4.3.0-1_all.deb",
                "dists/stable/InRelease",
                "dists/stable/Release.gpg",
            },
        )

    def test_yum_repodata_paths_from_repomd(self):
        repomd = """<?xml version="1.0" encoding="UTF-8"?>
<repomd xmlns="http://linux.duke.edu/metadata/repo">
  <data type="primary">
    <location href="primary.xml.gz"/>
  </data>
  <data type="filelists">
    <location href="filelists.xml.gz"/>
  </data>
</repomd>
"""
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False) as fh:
            fh.write(repomd)
            repomd_path = fh.name

        try:
            result = _source_bash_function("yum_repodata_paths_from_repomd", repomd_path)
        finally:
            Path(repomd_path).unlink(missing_ok=True)

        self.assertEqual(
            result.stdout.splitlines(),
            ["repodata/primary.xml.gz", "repodata/filelists.xml.gz"],
        )

    def test_yum_package_paths_from_primary(self):
        with tempfile.TemporaryDirectory() as tmp:
            repodata = Path(tmp)
            primary = """<?xml version="1.0" encoding="UTF-8"?>
<metadata xmlns="http://linux.duke.edu/metadata/common">
  <package type="rpm">
    <location href="packages/odpm-4.3.0-1.fc41.noarch.rpm"/>
  </package>
</metadata>
"""
            (repodata / "primary.xml").write_text(primary, encoding="utf-8")
            result = _source_bash_function(
                "yum_package_paths_from_primary", str(repodata)
            )
            self.assertEqual(
                result.stdout.splitlines(),
                ["packages/odpm-4.3.0-1.fc41.noarch.rpm"],
            )

    def test_preserve_script_is_executable(self):
        self.assertTrue(SCRIPT.is_file())
        self.assertTrue(SCRIPT.stat().st_mode & 0o111, msg=f"{SCRIPT.name} not executable")


if __name__ == "__main__":
    unittest.main()
