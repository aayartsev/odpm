"""Container runtime must not depend on host CLI packages directly."""

from __future__ import annotations

import ast
import importlib
import sys
import unittest
from pathlib import Path

_CONTAINER_ROOT = Path(__file__).resolve().parents[1] / "dev_project" / "inside_docker_app"
_FORBIDDEN_ROOTS = ("host", "host_cli")
_HOST_ONLY_MODULES = (
    "dev_project.plan",
    "dev_project.config.config",
    "dev_project.manifest.compat",
)


def _iter_container_python_files() -> list[Path]:
    return sorted(_CONTAINER_ROOT.rglob("*.py"))


def _imports_forbidden_host_modules(source: str) -> list[str]:
    tree = ast.parse(source)
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root = alias.name.split(".", 1)[0]
                if root in _FORBIDDEN_ROOTS:
                    hits.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split(".", 1)[0]
                if root in _FORBIDDEN_ROOTS:
                    hits.append(f"from {node.module} import ...")
            elif node.level and any(
                part in _FORBIDDEN_ROOTS for part in (node.module or "").split(".")
            ):
                hits.append(f"relative from {node.module!r}")
    return hits


class HostCliIsolationTests(unittest.TestCase):
    def test_container_modules_do_not_import_host_packages(self):
        violations: list[str] = []
        for path in _iter_container_python_files():
            hits = _imports_forbidden_host_modules(path.read_text(encoding="utf-8"))
            if hits:
                rel = path.relative_to(_CONTAINER_ROOT.parent.parent)
                violations.append(f"{rel}: {', '.join(hits)}")
        self.assertEqual(violations, [])

    def test_container_bootstrap_entry_does_not_import_host_packages(self):
        source = (
            _CONTAINER_ROOT / "container_bootstrap.py"
        ).read_text(encoding="utf-8")
        self.assertEqual(_imports_forbidden_host_modules(source), [])

    def test_run_odoo_entry_does_not_import_host_packages(self):
        source = (_CONTAINER_ROOT / "run_odoo.py").read_text(encoding="utf-8")
        self.assertEqual(_imports_forbidden_host_modules(source), [])

    def test_compose_start_command_import_does_not_load_ruamel(self):
        purge_prefixes = ("dev_project.compose", "dev_project.host")
        ruamel_modules = tuple(
            name
            for name in sys.modules
            if name == "ruamel" or name.startswith("ruamel.")
        )
        yaml_modules = tuple(
            name for name in sys.modules if name.startswith("dev_project.yaml")
        )
        preserved = {
            name: sys.modules.pop(name)
            for name in list(sys.modules)
            if name.startswith(purge_prefixes)
            or name in ruamel_modules
            or name in yaml_modules
        }
        try:
            importlib.import_module("dev_project.compose.start_command")
            for name in ruamel_modules + yaml_modules:
                self.assertNotIn(
                    name,
                    sys.modules,
                    msg=(
                        f"{name} must not load when importing compose.start_command "
                        "(container run_odoo path; ADR-005)"
                    ),
                )
            self.assertNotIn("ruamel", sys.modules)
            self.assertNotIn("dev_project.yaml", sys.modules)
        finally:
            sys.modules.update(preserved)

    def test_manifest_reader_import_does_not_load_ruamel(self):
        purge_prefixes = (
            "dev_project.manifest",
            "dev_project.compose",
            "dev_project.config",
        )
        ruamel_modules = tuple(
            name
            for name in sys.modules
            if name == "ruamel" or name.startswith("ruamel.")
        )
        yaml_modules = tuple(
            name for name in sys.modules if name.startswith("dev_project.yaml")
        )
        preserved = {
            name: sys.modules.pop(name)
            for name in list(sys.modules)
            if name.startswith(purge_prefixes)
            or name in ruamel_modules
            or name in yaml_modules
        }
        try:
            importlib.import_module("dev_project.manifest.reader")
            for name in ruamel_modules + yaml_modules:
                self.assertNotIn(
                    name,
                    sys.modules,
                    msg=(
                        f"{name} must not load when importing manifest.reader "
                        "(container config path; ADR-005)"
                    ),
                )
            self.assertNotIn("ruamel", sys.modules)
            self.assertNotIn("dev_project.yaml", sys.modules)
        finally:
            sys.modules.update(preserved)

    def test_config_payload_import_does_not_load_ruamel(self):
        """Golden-path container bootstrap imports config.payload via config package."""
        purge_prefixes = ("dev_project.",)
        ruamel_modules = tuple(
            name
            for name in sys.modules
            if name == "ruamel" or name.startswith("ruamel.")
        )
        yaml_modules = tuple(
            name for name in sys.modules if name.startswith("dev_project.yaml")
        )
        preserved = {
            name: sys.modules.pop(name)
            for name in list(sys.modules)
            if name.startswith(purge_prefixes)
            or name in ruamel_modules
            or name in yaml_modules
        }
        try:
            importlib.import_module("dev_project.config.payload")
            for name in ruamel_modules + yaml_modules:
                self.assertNotIn(
                    name,
                    sys.modules,
                    msg=(
                        f"{name} must not load when importing config.payload "
                        "(inside_docker_app virtualenv checker; ADR-005)"
                    ),
                )
            self.assertNotIn("ruamel", sys.modules)
            self.assertNotIn("dev_project.yaml", sys.modules)
        finally:
            sys.modules.update(preserved)

    def test_database_record_import_does_not_load_host_plan_or_config(self):
        purge_prefixes = ("dev_project.database",)
        preserved = {
            name: sys.modules.pop(name)
            for name in list(sys.modules)
            if name.startswith(purge_prefixes) or name in _HOST_ONLY_MODULES
        }
        try:
            importlib.import_module("dev_project.database.record")
            for name in _HOST_ONLY_MODULES:
                self.assertNotIn(
                    name,
                    sys.modules,
                    msg=f"{name} must not load when importing database.record from container",
                )
        finally:
            sys.modules.update(preserved)


if __name__ == "__main__":
    unittest.main()
