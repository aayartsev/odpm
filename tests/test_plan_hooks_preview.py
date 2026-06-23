"""Tests for manifest hook steps in odpm plan output."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from dev_project.extensions.context import ExtensionHostContext
from dev_project.plan.hooks_preview import (
    build_manifest_hook_plan_steps,
    insert_prepare_hook_steps,
    insert_runtime_hook_steps,
)
from dev_project.prepare.helpers import make_plan_step


class PlanHookPreviewTests(unittest.TestCase):
    def test_builds_post_prepare_and_pre_up_steps(self) -> None:
        ext = ExtensionHostContext(
            host=MagicMock(),
            repo_odpm_json="/tmp/odpm.json",
            manifest_hooks={
                "post_prepare": [["echo", "done"]],
                "pre_up": ["my.plugin"],
            },
        )
        steps = build_manifest_hook_plan_steps(ext)
        self.assertEqual([step.id for step in steps], ["hooks.post_prepare", "hooks.pre_up"])

    def test_insert_prepare_appends_post_prepare(self) -> None:
        prepare = [
            make_plan_step("git.materialize", "git", "run", True, "clone"),
            make_plan_step("compose.generate", "compose", "run", True, "gen"),
        ]
        hook = make_plan_step("hooks.post_prepare", "hooks", "run", False, "notify")
        merged = insert_prepare_hook_steps(prepare, (hook,))
        self.assertEqual(merged[-1].id, "hooks.post_prepare")

    def test_insert_runtime_places_pre_up_before_compose_up(self) -> None:
        runtime = [
            make_plan_step("ide.debug_profile", "ide", "noop", False, "ok"),
            make_plan_step("compose.up", "compose", "run", True, "up"),
        ]
        hook = make_plan_step("hooks.pre_up", "hooks", "run", True, "warmup")
        merged = insert_runtime_hook_steps(runtime, (hook,))
        self.assertEqual([step.id for step in merged], ["ide.debug_profile", "hooks.pre_up", "compose.up"])


if __name__ == "__main__":
    unittest.main()
