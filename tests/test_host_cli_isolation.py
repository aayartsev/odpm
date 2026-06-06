"""Container runtime must not depend on host_cli directly."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

_CONTAINER_ROOT = Path(__file__).resolve().parents[1] / "dev_project" / "inside_docker_app"
_SHIM_FILES = {"parse_args.py", "cli_params.py"}


def _iter_container_python_files() -> list[Path]:
    return sorted(
        path
        for path in _CONTAINER_ROOT.rglob("*.py")
        if path.name not in _SHIM_FILES
    )


def _imports_host_cli(source: str) -> list[str]:
    tree = ast.parse(source)
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "host_cli" or alias.name.startswith("host_cli."):
                    hits.append(f"import {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if node.module and (
                node.module == "host_cli" or node.module.startswith("host_cli.")
            ):
                hits.append(f"from {node.module} import ...")
            elif node.level and any(
                part == "host_cli"
                for part in (node.module or "").split(".")
            ):
                hits.append(f"relative from {node.module!r}")
    return hits


class HostCliIsolationTests(unittest.TestCase):
    def test_container_modules_do_not_import_host_cli(self):
        violations: list[str] = []
        for path in _iter_container_python_files():
            hits = _imports_host_cli(path.read_text(encoding="utf-8"))
            if hits:
                rel = path.relative_to(_CONTAINER_ROOT.parent.parent)
                violations.append(f"{rel}: {', '.join(hits)}")
        self.assertEqual(violations, [])

    def test_container_bootstrap_entry_does_not_import_host_cli(self):
        source = (
            _CONTAINER_ROOT / "container_bootstrap.py"
        ).read_text(encoding="utf-8")
        self.assertEqual(_imports_host_cli(source), [])

    def test_run_odoo_entry_does_not_import_host_cli(self):
        source = (_CONTAINER_ROOT / "run_odoo.py").read_text(encoding="utf-8")
        self.assertEqual(_imports_host_cli(source), [])


if __name__ == "__main__":
    unittest.main()
