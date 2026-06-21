"""Release package version contract (deb/rpm, pip, CLI)."""

from __future__ import annotations

import re
import tempfile
import unittest
from pathlib import Path

from dev_project import constants
from packaging.version import Version
from scripts.release_native_versions import (
    debian_upstream_version,
    parse_release_version,
    rpm_version_and_release,
)
from scripts.verify_release_tag_version import verify_release_tag_version
from tests.odpm_subprocess import run_odpm

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class ReleasePackagingVersionTests(unittest.TestCase):
    def test_odpm_version_aliases_release_version(self):
        self.assertEqual(constants.ODPM_VERSION, constants.RELEASE_VERSION)
        self.assertEqual(constants.RELEASE_VERSION, "4.4.3-beta")
        self.assertEqual(constants.LATEST_STABLE_RELEASE, "4.4.2")

    def test_manifest_contract_line_stays_separate_from_product_version(self):
        self.assertEqual(constants.MANIFEST_V1_CONTRACT_LINE, "4.0")
        self.assertNotEqual(constants.MANIFEST_V1_CONTRACT_LINE, constants.RELEASE_VERSION)

    def test_cli_version_matches_release_version(self):
        with tempfile.TemporaryDirectory() as tmp:
            completed = run_odpm("--version", cwd=tmp)
        self.assertEqual(completed.returncode, 0, msg=completed.stderr or completed.stdout)
        self.assertIn(
            f"odpm version: {constants.RELEASE_VERSION}",
            completed.stderr + completed.stdout,
        )

    def test_debian_changelog_matches_release_line(self):
        changelog = (PROJECT_ROOT / "debian" / "changelog").read_text(encoding="utf-8")
        deb_version = debian_upstream_version(constants.RELEASE_VERSION)
        self.assertRegex(
            changelog,
            rf"^odpm \({re.escape(deb_version)}-1\)",
            re.MULTILINE,
        )

    def test_rpm_spec_matches_release_line(self):
        spec = (PROJECT_ROOT / "packaging" / "odpm.spec").read_text(encoding="utf-8")
        rpm_version, rpm_release = rpm_version_and_release(constants.RELEASE_VERSION)
        self.assertIn("Version:        %{version}", spec)
        self.assertIn(f"%global version {rpm_version}", spec)
        self.assertIn(f"%global release {rpm_release}", spec)

    def test_release_version_parses_for_rpm(self):
        rpm_version, rpm_release = rpm_version_and_release(constants.RELEASE_VERSION)
        self.assertEqual(rpm_version, "4.4.3")
        self.assertEqual(rpm_release, "beta")
        base, suffix = parse_release_version(constants.RELEASE_VERSION)
        self.assertEqual(base, "4.4.3")
        self.assertEqual(suffix, "beta")

    def test_release_version_parses_for_debian(self):
        self.assertEqual(debian_upstream_version("4.4.3-beta"), "4.4.3~beta")
        self.assertEqual(debian_upstream_version("4.4.2-beta"), "4.4.2~beta")
        self.assertEqual(debian_upstream_version("4.4.2"), "4.4.2")

    def test_release_tag_matches_release_version(self):
        verify_release_tag_version(constants.RELEASE_VERSION)

    def test_release_tag_mismatch_raises(self):
        with self.assertRaises(ValueError):
            verify_release_tag_version("0.0.0")

    def test_wheel_version_uses_pep440_normalization(self):
        self.assertEqual(str(Version("4.4.2-beta")), "4.4.2b0")
        self.assertEqual(str(Version(constants.RELEASE_VERSION)), "4.4.3b0")

    def test_release_packages_prerelease_golden_path_gate(self):
        workflow = (
            PROJECT_ROOT / ".github" / "workflows" / "release-packages.yml"
        ).read_text(encoding="utf-8")
        golden = workflow.split("golden-path:", 1)[1].split("\n  publish:", 1)[0]
        self.assertIn("needs: deb", golden)
        self.assertIn("contains(github.ref, '-beta')", golden)
        self.assertIn("ODPM_GOLDEN_PATH_ENABLED", golden)
        self.assertIn("package-deb", golden)
        self.assertIn("ubuntu:24.04", golden)
        self.assertIn("Install smoke (built .deb", golden)
        self.assertIn("runuser -u odpm-smoke", golden)
        self.assertIn("grep -Fq", golden)
        self.assertNotIn("sudo apt-get", golden)
        self.assertIn("tests.integration.test_golden_path", golden)
        self.assertIn("needs: [deb, rpm, golden-path]", workflow)
        self.assertIn("needs.golden-path.result == 'skipped'", workflow)
        for job in ("publish-pypi:", "publish-pages:"):
            block = workflow.split(job, 1)[1].split("\n\n", 1)[0]
            self.assertIn("always()", block, msg=f"{job} must tolerate skipped golden-path")
            self.assertIn("needs.publish.result == 'success'", block)
            self.assertIn("startsWith(github.ref, 'refs/tags/')", block)
        pypi_block = workflow.split("publish-pypi:", 1)[1].split("\n  publish-pages:", 1)[0]
        prod_section = pypi_block.split("Publish to production PyPI", 1)[1]
        self.assertIn("skip-existing: true", prod_section)
        test_section = pypi_block.split("Publish to TestPyPI", 1)[1]
        self.assertIn("skip-existing: true", test_section)


if __name__ == "__main__":
    unittest.main()
