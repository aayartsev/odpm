"""Plan preview evaluate helpers should not read Config directly."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

PLAN_DIR = Path(__file__).resolve().parents[1] / "dev_project" / "plan"

COMPOSE_EVALUATE_HELPERS = frozenset(
    {
        "compose_service_needs_update",
        "compose_generate_needs_execute",
        "docker_compose_matches_preview",
        "_project_env_has_volume_map",
    }
)


def _function_source_lines(path: Path, function_names: frozenset[str]) -> dict[str, str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    lines = path.read_text(encoding="utf-8").splitlines()
    found: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef):
            continue
        if node.name not in function_names:
            continue
        segment = lines[node.lineno - 1 : node.end_lineno]
        found[node.name] = "\n".join(segment)
    missing = function_names - found.keys()
    if missing:
        raise AssertionError(f"{path.name} missing evaluate helpers: {sorted(missing)}")
    return found


class PlanConfigCouplingTests(unittest.TestCase):
    def test_locks_preview_does_not_reference_config(self):
        path = PLAN_DIR / "locks_preview.py"
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("ctx.config", text)
        self.assertNotIn("config.", text)
        self.assertNotIn("from ..config import Config", text)

    def test_compose_preview_evaluate_helpers_do_not_reference_config(self):
        path = PLAN_DIR / "compose_preview.py"
        offenders: list[str] = []
        for name, source in _function_source_lines(
            path, COMPOSE_EVALUATE_HELPERS
        ).items():
            if "ctx.config" in source or "config." in source:
                offenders.append(name)
        self.assertEqual(
            offenders,
            [],
            msg=(
                "compose preview evaluate helpers must use ctx.host_ctx / "
                f"PrepareContext ports: {offenders}"
            ),
        )


if __name__ == "__main__":
    unittest.main()
