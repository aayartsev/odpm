"""Builtin recipe: apply modules from developing git diff (server)."""

from __future__ import annotations

import json
from typing import Sequence

from ...errors import ConfigError
from ...translations import _
from ..types import OdpmStep, RecipeContext, RecipeParam


class ApplyModulesFromDiffRecipe:
    name = "apply-modules-from-diff"
    description = (
        "Classify modules since a git baseline, run -i/-u with --stop-after-init, "
        "then record the deploy marker (intended for ODPM_SCENARIO=server)."
    )

    def __init__(self) -> None:
        self._phase = 0
        self._record_done = False

    def params(self) -> Sequence[RecipeParam]:
        return (
            RecipeParam(
                name="database",
                required=True,
                env="ODPM_RUN_DATABASE",
                description="Odoo database name (-d)",
            ),
            RecipeParam(
                name="diff_base",
                required=False,
                env="ODPM_DIFF_BASE",
                description="Optional git baseline for modules diff",
            ),
        )

    def reset(self, ctx: RecipeContext) -> None:
        self._phase = 0
        self._record_done = False
        ctx.scratch.clear()

    def next_step(self, ctx: RecipeContext) -> OdpmStep | None:
        if self._phase == 0:
            self._phase = 1
            argv = ["modules", "diff", "--format", "json"]
            diff_base = (ctx.params.get("diff_base") or "").strip()
            if diff_base:
                argv = [
                    "modules",
                    "diff",
                    "--diff-base",
                    diff_base,
                    "--format",
                    "json",
                ]
            return OdpmStep(
                argv=tuple(argv),
                capture=True,
                timeout=120.0,
                execute_even_if_dry_run=True,
                label="modules-diff",
            )

        if self._phase == 1:
            self._ingest_diff(ctx)
            self._phase = 2
            init_csv = str(ctx.scratch.get("init_modules") or "")
            update_csv = str(ctx.scratch.get("update_modules") or "")
            if init_csv or update_csv:
                apply_argv: list[str] = ["-d", ctx.params["database"]]
                if init_csv:
                    apply_argv.extend(["-i", init_csv])
                if update_csv:
                    apply_argv.extend(["-u", update_csv])
                apply_argv.extend(["--odoo-bin", "--stop-after-init"])
                return OdpmStep(
                    argv=tuple(apply_argv),
                    capture=False,
                    timeout=None,
                    execute_even_if_dry_run=False,
                    label="modules-apply",
                )

        if self._phase >= 2 and not self._record_done:
            self._record_done = True
            return OdpmStep(
                argv=("modules", "record-applied"),
                capture=False,
                timeout=120.0,
                execute_even_if_dry_run=False,
                label="record-applied",
            )
        return None

    def _ingest_diff(self, ctx: RecipeContext) -> None:
        if ctx.scratch.get("init_modules") is not None:
            return
        if not ctx.step_results:
            raise ConfigError(_("modules diff produced no step result."))
        last = ctx.step_results[-1]
        if last.skipped:
            raise ConfigError(_("modules diff step was skipped unexpectedly."))
        try:
            payload = json.loads(last.stdout or "{}")
        except json.JSONDecodeError as exc:
            raise ConfigError(
                _("modules diff JSON parse failed: {ERROR}").format(ERROR=exc)
            ) from exc
        if not isinstance(payload, dict):
            raise ConfigError(_("modules diff JSON must be an object."))
        ctx.scratch["init_modules"] = str(payload.get("init_modules") or "").strip()
        ctx.scratch["update_modules"] = str(
            payload.get("update_modules") or ""
        ).strip()
        ctx.scratch["base"] = str(payload.get("base") or "")
        ctx.scratch["head"] = str(payload.get("head") or "")
