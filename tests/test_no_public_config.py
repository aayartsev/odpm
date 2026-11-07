"""CI gate: no public Config / AssembledProject outside config/ (+ ports for handle)."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEV = ROOT / "dev_project"

# Consumers may not import these symbols. Exception: config/ package and host/ports.py
# (handle wraps the private assembled snapshot).
ALLOWED_ASSEMBLED_DIRS = frozenset(
    {
        "dev_project/config",
    }
)
ALLOWED_ASSEMBLED_FILES = frozenset(
    {
        "dev_project/host/ports.py",
    }
)

FORBIDDEN_BOOTSTRAP_CONFIG = "bootstrap.config"


def _py_files(root: Path) -> list[Path]:
    return sorted(p for p in root.rglob("*.py") if p.is_file())


def _rel(path: Path) -> str:
    return str(path.relative_to(ROOT)).replace("\\", "/")


def _allowed_assembled_import(rel: str) -> bool:
    if rel in ALLOWED_ASSEMBLED_FILES:
        return True
    for prefix in ALLOWED_ASSEMBLED_DIRS:
        if rel == prefix or rel.startswith(prefix + "/"):
            return True
    return False


class NoPublicConfigGateTests(unittest.TestCase):
    def test_package_does_not_export_config_or_assembled(self):
        import dev_project.config as config_pkg

        self.assertFalse(hasattr(config_pkg, "Config"))
        self.assertFalse(hasattr(config_pkg, "AssembledProject"))

    def test_no_bootstrap_config_outside_ports_and_config(self):
        offenders: list[str] = []
        for path in _py_files(DEV):
            rel = _rel(path)
            if rel == "dev_project/host/ports.py" or rel.startswith("dev_project/config/"):
                continue
            text = path.read_text(encoding="utf-8")
            if FORBIDDEN_BOOTSTRAP_CONFIG in text:
                offenders.append(rel)
        self.assertEqual(offenders, [], msg=f"bootstrap.config still present: {offenders}")

    def test_no_assembled_project_import_outside_allowlist(self):
        offenders: list[str] = []
        for path in _py_files(DEV):
            rel = _rel(path)
            if _allowed_assembled_import(rel):
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.ImportFrom):
                    names = {alias.name for alias in node.names}
                    if "AssembledProject" in names or "Config" in names:
                        # ConfigError etc. not ImportFrom name Config alone when aliased
                        bad = names & {"AssembledProject", "Config"}
                        if bad:
                            offenders.append(f"{rel}:{node.lineno}:{sorted(bad)}")
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        if alias.name in {"AssembledProject", "Config"}:
                            offenders.append(f"{rel}:{node.lineno}:{alias.name}")
        self.assertEqual(offenders, [], msg=f"forbidden imports: {offenders}")

    def test_bootstrap_handle_has_no_public_config_field(self):
        from dataclasses import fields

        from dev_project.host.ports import BootstrapHandle

        names = {f.name for f in fields(BootstrapHandle)}
        self.assertIn("_assembled", names)
        self.assertNotIn("config", names)

    def test_assembled_project_lacks_handle_facades(self):
        from dev_project.config.config import AssembledProject

        for name in (
            "handle_git_link",
            "ensure_git_repo_symlink",
            "ensure_developing_repo_symlinks",
            "apply_nested_compatibility",
            "generate_odoo_conf_docker_data",
        ):
            self.assertFalse(
                hasattr(AssembledProject, name),
                msg=f"AssembledProject still exposes facade {name}",
            )


if __name__ == "__main__":
    unittest.main()
