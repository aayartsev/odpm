"""Local plugin fixture for hooks integration E2E (imported from .odpm/plugins/)."""

from __future__ import annotations

from pathlib import Path

from dev_project.extensions.context import ExtensionHostContext
from dev_project.extensions.registry import register_hook_runner

PLUGIN_ID = "e2e.local.hooks"
MARKER_REL_PATH = ".odpm/plugin-hook.ok"


class HooksE2eRunner:
    name = PLUGIN_ID

    def run_post_prepare(self, ctx: ExtensionHostContext) -> None:
        marker = Path(ctx.project_dir) / MARKER_REL_PATH
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text("ok\n", encoding="utf-8")


register_hook_runner(PLUGIN_ID, HooksE2eRunner())
