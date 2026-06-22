"""Plan preview evaluate helpers should not read Config directly."""

from __future__ import annotations

import ast
import unittest
from pathlib import Path

PLAN_DIR = Path(__file__).resolve().parents[1] / "dev_project" / "plan"
PREPARE_HELPERS = (
    Path(__file__).resolve().parents[1] / "dev_project" / "prepare" / "helpers.py"
)

COMPOSE_EVALUATE_HELPERS = frozenset(
    {
        "compose_service_needs_update",
        "compose_generate_needs_execute",
        "docker_compose_matches_preview",
        "_project_env_has_volume_map",
    }
)

DIFF_HELPERS = frozenset(
    {
        "preview_dockerignore_content",
        "diff_debug_profile",
        "diff_runtime_config_text",
        "diff_dockerignore",
        "preview_docker_compose_content",
        "diff_docker_compose_text",
        "diff_secrets_materialize_summary",
    }
)

COMPOSE_RUNTIME_HELPERS = frozenset(
    {
        "compose_up_force_recreate_value",
        "evaluate_compose_up_plan",
    }
)

LOCK_HELPER_FUNCTIONS = frozenset(
    {
        "lock_verify_available",
        "manifest_lock_apply_available",
        "lock_source_label",
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


def _assert_no_config_coupling(
    test_case: unittest.TestCase,
    path: Path,
    function_names: frozenset[str],
    *,
    label: str,
) -> None:
    offenders: list[str] = []
    for name, source in _function_source_lines(path, function_names).items():
        if "ctx.config" in source or "config." in source:
            offenders.append(name)
    test_case.assertEqual(
        offenders,
        [],
        msg=f"{label} must use host_ctx / typed ports: {offenders}",
    )


class PlanConfigCouplingTests(unittest.TestCase):
    def test_locks_preview_does_not_reference_config(self):
        path = PLAN_DIR / "locks_preview.py"
        text = path.read_text(encoding="utf-8")
        self.assertNotIn("ctx.config", text)
        self.assertNotIn("config.", text)
        self.assertNotIn("from ..config import Config", text)

    def test_compose_preview_evaluate_helpers_do_not_reference_config(self):
        _assert_no_config_coupling(
            self,
            PLAN_DIR / "compose_preview.py",
            COMPOSE_EVALUATE_HELPERS,
            label="compose preview evaluate helpers",
        )

    def test_diff_helpers_do_not_reference_config(self):
        _assert_no_config_coupling(
            self,
            PLAN_DIR / "diff.py",
            DIFF_HELPERS,
            label="plan diff helpers",
        )

    def test_compose_runtime_helpers_do_not_reference_config(self):
        _assert_no_config_coupling(
            self,
            PLAN_DIR / "compose_runtime.py",
            COMPOSE_RUNTIME_HELPERS,
            label="compose runtime plan helpers",
        )

    def test_prepare_lock_helpers_do_not_reference_ctx_config(self):
        _assert_no_config_coupling(
            self,
            PREPARE_HELPERS,
            LOCK_HELPER_FUNCTIONS,
            label="prepare lock helpers",
        )


if __name__ == "__main__":
    unittest.main()
