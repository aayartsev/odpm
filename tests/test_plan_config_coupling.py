"""Plan preview evaluate helpers should not read Config directly."""

from __future__ import annotations

import ast
import re
import unittest
from pathlib import Path

PLAN_DIR = Path(__file__).resolve().parents[1] / "dev_project" / "plan"
PREPARE_HELPERS = (
    Path(__file__).resolve().parents[1] / "dev_project" / "prepare" / "helpers.py"
)

# ``bootstrap.config`` is allowed on the narrowed BootstrapHandle boundary (D3).
_FORBIDDEN_CONFIG_ACCESS = re.compile(r"ctx\.config|(?<!bootstrap\.)config\.")

MANIFEST_PREVIEW_MODULES = frozenset(
    {
        "patches_preview.py",
        "fragments_preview.py",
        "hooks_preview.py",
    }
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
        if _FORBIDDEN_CONFIG_ACCESS.search(source):
            offenders.append(name)
    test_case.assertEqual(
        offenders,
        [],
        msg=f"{label} must use host_ctx / typed ports: {offenders}",
    )


def _assert_module_has_no_config_coupling(test_case: unittest.TestCase, path: Path) -> None:
    text = path.read_text(encoding="utf-8")
    test_case.assertNotIn("ctx.config", text)
    test_case.assertIsNone(
        _FORBIDDEN_CONFIG_ACCESS.search(text),
        msg=f"{path.name} must not reference Config outside bootstrap handle",
    )
    test_case.assertNotIn("from ..config import Config", text)


class PlanConfigCouplingTests(unittest.TestCase):
    def test_locks_preview_does_not_reference_config(self):
        _assert_module_has_no_config_coupling(self, PLAN_DIR / "locks_preview.py")

    def test_manifest_preview_modules_do_not_reference_config(self):
        for module_name in sorted(MANIFEST_PREVIEW_MODULES):
            _assert_module_has_no_config_coupling(self, PLAN_DIR / module_name)

    def test_manifest_preview_helpers_do_not_reference_config(self):
        for module_name, function_names in (
            ("patches_preview.py", frozenset({"build_compose_patch_plan_steps"})),
            (
                "fragments_preview.py",
                frozenset({"build_compose_fragment_service_plan_steps"}),
            ),
            (
                "database_preview.py",
                frozenset({"collect_database_drift_warnings_for_host"}),
            ),
        ):
            _assert_no_config_coupling(
                self,
                PLAN_DIR / module_name,
                function_names,
                label=f"{module_name} evaluate helpers",
            )

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
