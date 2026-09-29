"""Builtin recipe: pull remote Odoo backup then restore into a local database."""

from __future__ import annotations

from typing import Sequence

from ...errors import ConfigError
from ...translations import _
from ..types import OdpmStep, RecipeContext, RecipeParam


class PullRemoteDbRecipe:
    name = "pull-remote-db"
    description = (
        "Download a zip from a remote Odoo manager into BACKUP_DIR, then "
        "odpm --db-restore into a local database (developer/server; "
        "set ODPM_REMOTE_DB_MASTER_PWD)."
    )

    def __init__(self) -> None:
        self._phase = 0

    def params(self) -> Sequence[RecipeParam]:
        return (
            RecipeParam(
                name="database",
                required=True,
                env="ODPM_RUN_DATABASE",
                description="Local Odoo database name (-d) for restore",
            ),
            RecipeParam(
                name="url",
                required=True,
                env="ODPM_REMOTE_DB_URL",
                description="Remote Odoo base URL",
            ),
            RecipeParam(
                name="remote_db",
                required=True,
                env="ODPM_REMOTE_DB_NAME",
                description="Remote database name to back up",
            ),
        )

    def reset(self, ctx: RecipeContext) -> None:
        self._phase = 0
        ctx.scratch.clear()

    def next_step(self, ctx: RecipeContext) -> OdpmStep | None:
        if self._phase == 0:
            self._phase = 1
            return OdpmStep(
                argv=(
                    "database",
                    "pull",
                    "--url",
                    ctx.params["url"],
                    "--remote-db",
                    ctx.params["remote_db"],
                ),
                capture=True,
                timeout=None,
                execute_even_if_dry_run=False,
                label="database-pull",
            )

        if self._phase == 1:
            if ctx.dry_run and ctx.step_results and ctx.step_results[-1].skipped:
                ctx.scratch["archive"] = "<archive.zip>"
            else:
                self._ingest_archive_name(ctx)
            self._phase = 2
            archive = str(ctx.scratch.get("archive") or "").strip()
            return OdpmStep(
                argv=(
                    "-d",
                    ctx.params["database"],
                    "--db-restore",
                    archive,
                ),
                capture=False,
                timeout=None,
                execute_even_if_dry_run=False,
                label="db-restore",
            )
        return None

    def _ingest_archive_name(self, ctx: RecipeContext) -> None:
        if ctx.scratch.get("archive") is not None:
            return
        if not ctx.step_results:
            raise ConfigError(_("database pull produced no step result."))
        last = ctx.step_results[-1]
        if last.skipped:
            raise ConfigError(_("database pull step was skipped unexpectedly."))
        archive = (last.stdout or "").strip().splitlines()
        name = archive[-1].strip() if archive else ""
        if not name:
            raise ConfigError(_("database pull did not print an archive name."))
        ctx.scratch["archive"] = name
