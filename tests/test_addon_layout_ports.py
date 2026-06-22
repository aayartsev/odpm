"""Addon layout callers must read module catalogs via host_ctx.addon_layout."""

from __future__ import annotations

import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

ADDON_LAYOUT_CALLER_FILES = (
    "dev_project/symlinks/manager.py",
    "dev_project/project_env/volume_mapper.py",
    "dev_project/project_env/services/python_analysis_paths.py",
)

CATALOG_ATTR = "catalogs_of_modules_data"

FORBIDDEN_PATTERNS = (
    re.compile(r"config\.catalogs_of_modules_data"),
    re.compile(r"config\.addon_layout\.catalogs_of_modules_data"),
    re.compile(r"config\.list_of_developing_project_subprojects_data"),
    re.compile(
        r'getattr\s*\(\s*(?:self\.)?config\s*,\s*["\']catalogs_of_modules_data["\']'
    ),
    re.compile(
        r'getattr\s*\(\s*(?:self\.)?config\s*,\s*["\']list_of_developing_project_subprojects_data["\']'
    ),
)


class AddonLayoutPortsTests(unittest.TestCase):
    def test_addon_layout_callers_forbid_config_shim_access(self):
        offenders: list[str] = []
        for rel in ADDON_LAYOUT_CALLER_FILES:
            text = (PROJECT_ROOT / rel).read_text(encoding="utf-8")
            for pattern in FORBIDDEN_PATTERNS:
                if pattern.search(text):
                    offenders.append(f"{rel}: matches {pattern.pattern!r}")
        self.assertEqual(
            offenders,
            [],
            msg="read addon catalogs through host_ctx.addon_layout, not Config shims",
        )

    def test_catalog_access_lines_use_host_ctx_addon_layout(self):
        offenders: list[str] = []
        for rel in ADDON_LAYOUT_CALLER_FILES:
            for lineno, line in enumerate(
                (PROJECT_ROOT / rel).read_text(encoding="utf-8").splitlines(),
                start=1,
            ):
                stripped = line.strip()
                if CATALOG_ATTR not in stripped or stripped.startswith("#"):
                    continue
                if "host_ctx.addon_layout" not in stripped and "_host_ctx.addon_layout" not in stripped:
                    offenders.append(f"{rel}:{lineno}: {stripped}")
        self.assertEqual(
            offenders,
            [],
            msg="catalogs_of_modules_data access must go through host_ctx.addon_layout",
        )


if __name__ == "__main__":
    unittest.main()
