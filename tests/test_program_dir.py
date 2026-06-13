"""Tests for program_dir resolution (legacy copy vs pip install)."""

import tempfile
import unittest
from pathlib import Path

from dev_project import constants
from dev_project.program_dir import resolve_program_dir

PROJECT_ROOT = Path(__file__).resolve().parents[1]


class ResolveProgramDirTests(unittest.TestCase):
    def test_explicit_legacy_repo_root(self):
        self.assertEqual(
            resolve_program_dir(str(PROJECT_ROOT)),
            str(PROJECT_ROOT.resolve()),
        )

    def test_explicit_missing_bundle_falls_back_to_installed_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            resolved = resolve_program_dir(tmp)
        self.assertTrue(
            (Path(resolved) / constants.DEV_PROJECT_DIR / "templates").is_dir()
        )

    def test_default_uses_installed_dev_project_parent(self):
        resolved = resolve_program_dir()
        self.assertTrue(
            (Path(resolved) / constants.DEV_PROJECT_DIR / "templates").is_dir()
        )
        self.assertEqual(resolved, str(PROJECT_ROOT.resolve()))


if __name__ == "__main__":
    unittest.main()
