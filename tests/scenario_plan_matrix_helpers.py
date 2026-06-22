"""Shared helpers for scenario plan matrix tests."""

from __future__ import annotations

import io
import json
import os
import contextlib
from pathlib import Path
from typing import Any

from dev_project import constants
from dev_project.git.deps_lock import DepsLock, LockEntry, save_deps_lock
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.host.cli.parse_args import parse_cli_args
from dev_project.manifest.commands import run_manifest_command
from dev_project.odpm_pipeline import OdpmPipeline
from dev_project.plan import OdpmPlan, OdpmPlanner
from dev_project.plan.format import format_plan_json, plan_has_required_changes
from dev_project.prepare import evaluate_prepare_plan, make_prepare_context
from dev_project.prepare.steps_compose import exec_compose_generate, exec_compose_service

from tests.plan_smoke_helpers import repo_root


def program_dir() -> str:
    return str(repo_root())


def build_matrix_plan(
    project_dir: Path,
    cli_args: OdpmCliArgs,
) -> tuple[OdpmPlan, OdpmPipeline]:
    pipeline = OdpmPipeline(
        cli_args,
        program_dir(),
        start_dir=str(project_dir),
    )
    pipeline.setup(for_plan=True)
    plan = OdpmPlanner.build(
        pipeline.config,
        cli_args,
        pipeline.project_environment,
    )
    return plan, pipeline


def plan_step(plan: OdpmPlan, step_id: str):
    return next(step for step in plan.steps if step.id == step_id)


def plan_has_step(plan: OdpmPlan, step_id: str) -> bool:
    return any(step.id == step_id for step in plan.steps)


def prepare_step_outcome(
    pipeline: OdpmPipeline,
    cli_args: OdpmCliArgs,
    step_id: str,
) -> str:
    ctx = make_prepare_context(
        pipeline.config,
        pipeline.project_environment,
        pipeline.system_checker,
        cli_args,
    )
    return next(
        step.outcome
        for step in evaluate_prepare_plan(ctx)
        if step.id == step_id
    )


def seed_v1_deps_lock(project_dir: Path, *, platform_uri: str, commit: str = "e" * 40) -> None:
    """Write a minimal v1 deps.lock.json for lock-source plan warnings."""
    lock = DepsLock(
        platform=LockEntry(
            url=platform_uri,
            commit=commit,
            kind="file",
        )
    )
    save_deps_lock(str(project_dir / constants.DEPS_LOCK_REL_PATH), lock)


def seed_locks_drift(project_dir: Path, *, platform_uri: str) -> None:
    """Write mismatched locks.git (manifest) and deps.lock.json on disk."""
    manifest_commit = "a" * 40
    file_commit = "b" * 40

    developing = project_dir / "developing"
    odpm_path = developing / "odpm.json"
    odpm_json = json.loads(odpm_path.read_text(encoding="utf-8"))
    odpm_json.setdefault("locks", {})
    odpm_json["locks"]["git"] = {platform_uri: manifest_commit}
    odpm_path.write_text(json.dumps(odpm_json, indent=2) + "\n", encoding="utf-8")

    lock = DepsLock(
        platform=LockEntry(
            url=platform_uri,
            commit=file_commit,
            kind="file",
        )
    )
    save_deps_lock(
        str(project_dir / constants.DEPS_LOCK_REL_PATH),
        lock,
    )


def seed_matching_v2_locks(project_dir: Path, *, platform_uri: str) -> None:
    """Align locks.git and deps.lock.json for v2 manifest (no drift)."""
    commit = "c" * 40
    developing = project_dir / "developing"
    odpm_path = developing / "odpm.json"
    odpm_json = json.loads(odpm_path.read_text(encoding="utf-8"))
    odpm_json.setdefault("locks", {})
    odpm_json["locks"]["git"] = {platform_uri: commit}
    odpm_path.write_text(json.dumps(odpm_json, indent=2) + "\n", encoding="utf-8")

    lock = DepsLock(
        platform=LockEntry(
            url=platform_uri,
            commit=commit,
            kind="file",
        )
    )
    save_deps_lock(
        str(project_dir / constants.DEPS_LOCK_REL_PATH),
        lock,
    )


def sync_idle_compose_state(project_dir: Path) -> None:
    """Materialize compose runtime once so compose.service/generate plan as noop."""
    plan, pipeline = build_matrix_plan(
        project_dir,
        OdpmCliArgs(plan=True, skip_start=True, no_git_update=True),
    )
    ctx = make_prepare_context(
        pipeline.config,
        pipeline.project_environment,
        pipeline.system_checker,
        OdpmCliArgs(skip_start=True, no_git_update=True),
    )
    exec_compose_service(ctx)
    exec_compose_generate(ctx)


def invalid_v2_manifest_payload(*, base: dict[str, Any]) -> dict[str, Any]:
    payload = dict(base)
    payload["services"] = {"bad": {"ports": ["1:1"]}}
    return payload


@contextlib.contextmanager
def matrix_home(home: Path):
    previous = os.environ.get("HOME")
    os.environ["HOME"] = str(home)
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("HOME", None)
        else:
            os.environ["HOME"] = previous


def run_matrix_plan_cli(project_dir: Path, home: Path, *argv: str) -> tuple[int, str]:
    """Run odpm plan in-process (same interpreter as unit tests)."""
    args = parse_cli_args(["plan", *argv])
    with matrix_home(home):
        pipeline = OdpmPipeline(args, program_dir(), start_dir=str(project_dir))
        pipeline.setup(for_plan=True)
        if args.plan_format == "json":
            plan = OdpmPlanner.build(
                pipeline.config,
                args,
                pipeline.project_environment,
            )
            exit_code = 0
            if args.plan_strict and plan_has_required_changes(plan):
                exit_code = 1
            return exit_code, format_plan_json(
                plan, pipeline.project_environment.host_ctx, args
            )
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            exit_code = pipeline.print_plan()
        return exit_code, buffer.getvalue()


def run_matrix_manifest_cli(
    project_dir: Path,
    home: Path,
    *argv: str,
) -> tuple[int, str]:
    """Run odpm manifest subcommand in-process."""
    args = parse_cli_args(["manifest", *argv])
    with matrix_home(home):
        pipeline = OdpmPipeline(args, program_dir(), start_dir=str(project_dir))
        pipeline.setup(for_plan=True)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            exit_code = run_manifest_command(args, pipeline.config)
        return exit_code, buffer.getvalue()

