"""Plan steps for layered CI image hit/miss (ADR-027)."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..host.cli import params as cli_params
from ..image_layers.fingerprint import (
    compute_app_fingerprint,
    compute_deps_fingerprint,
    compute_lint_fingerprint,
    compute_platform_fingerprint,
    compute_venv_fingerprint,
    layer_image_ref,
)
from ..image_layers.registry import image_ref_exists
from ..system_check_policy import environ_from_host_context
from .core import PlanStep
from .l10n import plan_msg

if TYPE_CHECKING:
    from ..host.cli.args import OdpmCliArgs
    from ..host.context import HostProjectContext
    from ..host.ports import BootstrapHandle, RuntimePorts


def _remote_for_plan(
    bootstrap: BootstrapHandle,
    host_ctx: HostProjectContext,
    args: OdpmCliArgs,
) -> bool:
    from ..project_env.image_build.resolve import resolve_ci_image_push

    environ = environ_from_host_context(host_ctx)
    push = resolve_ci_image_push(args, environ=environ)
    import os

    registry = os.environ.get("ODPM_BASE_IMAGE_REGISTRY") or os.environ.get(
        "CI_REGISTRY_IMAGE", ""
    )
    return bool(push or registry)


def _layer_description(layer: str) -> str:
    mapping = {
        "base": plan_msg("image base ensure"),
        "platform": plan_msg("image platform ensure"),
        "venv": plan_msg("image venv ensure"),
        "deps": plan_msg("image deps ensure"),
        "app": plan_msg("image app ensure"),
        "lint": plan_msg("image lint ensure"),
    }
    return mapping.get(layer, plan_msg("image layer analysis"))


def _presence_step(
    *,
    step_id: str,
    layer: str,
    ref: str | None,
    remote: bool,
    required: bool,
    noop_reason: str | None = None,
) -> PlanStep:
    description = _layer_description(layer)
    if noop_reason is not None:
        return PlanStep(
            step_id,
            description,
            "noop",
            False,
            plan_msg(noop_reason),
        )
    assert ref is not None
    try:
        # Plan never forces rebuild; FORCE is for ensure only.
        exists = image_ref_exists(ref, remote=remote, force=False)
    except Exception as exc:  # noqa: BLE001 — plan must stay soft
        return PlanStep(
            step_id,
            description,
            "run",
            required,
            plan_msg("presence check failed: {ERR}").format(ERR=exc),
        )
    if exists:
        return PlanStep(
            step_id,
            description,
            "noop",
            False,
            plan_msg("hit {REF}").format(REF=ref),
        )
    return PlanStep(
        step_id,
        description,
        "run",
        required,
        plan_msg("miss {REF}").format(REF=ref),
    )


def build_image_layer_plan_steps(
    bootstrap: BootstrapHandle,
    host_ctx: HostProjectContext,
    args: OdpmCliArgs,
) -> tuple[PlanStep, ...]:
    """Fingerprint + hit/miss rows for ``odpm plan`` after sources."""
    if not getattr(host_ctx.policy, "allow_build_image", False):
        return ()
    # Always show analysis in ci; also when user asked build / image / stop-after.
    show = (
        args.build_image
        or args.command == cli_params.BUILD_SUBCOMMAND
        or args.command == cli_params.IMAGE_SUBCOMMAND
        or getattr(args, "stop_after", None) == cli_params.STOP_AFTER_SOURCES
        or getattr(host_ctx.policy, "scenario", None) == "ci"
    )
    if not show:
        return ()

    try:
        return _build_image_layer_plan_steps_inner(bootstrap, host_ctx, args)
    except Exception as exc:  # noqa: BLE001 — plan must stay soft
        return (
            PlanStep(
                "image.layers",
                plan_msg("image layer analysis"),
                "skip",
                False,
                plan_msg("layer analysis unavailable: {ERR}").format(ERR=exc),
            ),
        )


def _build_image_layer_plan_steps_inner(
    bootstrap: BootstrapHandle,
    host_ctx: HostProjectContext,
    args: OdpmCliArgs,
) -> tuple[PlanStep, ...]:
    # Fingerprint helpers still duck-type the assembled snapshot until F.
    assembled = bootstrap  # duck-typed fingerprint surface
    program_dir = str(host_ctx.program_dir)
    remote = _remote_for_plan(bootstrap, host_ctx, args)
    steps: list[PlanStep] = []

    steps.append(
        PlanStep(
            "image.base",
            _layer_description("base"),
            "run",
            True,
            plan_msg("base ensure (ADR-019 stamp / rebuild if stale)"),
        )
    )

    platform_fp = compute_platform_fingerprint(assembled, program_dir=program_dir)
    platform_ref = layer_image_ref(
        assembled, layer="platform", fingerprint=platform_fp
    )
    steps.append(
        _presence_step(
            step_id="image.platform",
            layer="platform",
            ref=platform_ref,
            remote=remote,
            required=True,
        )
    )

    venv_fp = compute_venv_fingerprint(
        assembled, program_dir=program_dir, platform_ref=platform_ref
    )
    venv_ref = layer_image_ref(assembled, layer="venv", fingerprint=venv_fp)
    steps.append(
        _presence_step(
            step_id="image.venv",
            layer="venv",
            ref=venv_ref,
            remote=remote,
            required=True,
        )
    )

    deps_fp = compute_deps_fingerprint(
        assembled, program_dir=program_dir, platform_ref=venv_ref
    )
    if deps_fp is None:
        steps.append(
            _presence_step(
                step_id="image.deps",
                layer="deps",
                ref=None,
                remote=remote,
                required=False,
                noop_reason="no dependencies — layer not required",
            )
        )
        parent_ref = venv_ref
    else:
        deps_ref = layer_image_ref(assembled, layer="deps", fingerprint=deps_fp)
        steps.append(
            _presence_step(
                step_id="image.deps",
                layer="deps",
                ref=deps_ref,
                remote=remote,
                required=True,
            )
        )
        parent_ref = deps_ref

    try:
        from ..image_layers.ensure import _developing_git_sha  # noqa: PLC0415
        import os

        developing_sha = _developing_git_sha(bootstrap)
        secrets_baked = os.environ.get("ODPM_BAKE_SECRETS", "").strip() in {
            "1",
            "true",
            "True",
            "yes",
            "YES",
        }
        app_fp = compute_app_fingerprint(
            assembled,
            program_dir=program_dir,
            parent_ref=parent_ref,
            developing_git_sha=developing_sha,
            secrets_baked=secrets_baked,
        )
        app_ref = layer_image_ref(assembled, layer="app", fingerprint=app_fp)
        steps.append(
            _presence_step(
                step_id="image.app",
                layer="app",
                ref=app_ref,
                remote=remote,
                required=True,
            )
        )
        if args.image_tag:
            steps.append(
                PlanStep(
                    "image.app.publish",
                    _layer_description("app"),
                    "noop",
                    False,
                    plan_msg("app FROM {PARENT}; publish tag {TAG}").format(
                        PARENT=parent_ref, TAG=args.image_tag
                    ),
                )
            )
    except Exception as exc:  # noqa: BLE001 — soft
        steps.append(
            PlanStep(
                "image.app",
                _layer_description("app"),
                "run",
                True,
                plan_msg("app FROM {PARENT}").format(PARENT=parent_ref)
                + f" ({exc})",
            )
        )

    from pathlib import Path

    if (Path(host_ctx.project_dir) / ".pre-commit-config.yaml").is_file():
        lint_fp = compute_lint_fingerprint(
            assembled, program_dir=program_dir, platform_fp=platform_fp
        )
        lint_ref = layer_image_ref(assembled, layer="lint", fingerprint=lint_fp)
        steps.append(
            _presence_step(
                step_id="image.lint",
                layer="lint",
                ref=lint_ref,
                remote=remote,
                required=False,
            )
        )
    else:
        steps.append(
            _presence_step(
                step_id="image.lint",
                layer="lint",
                ref=None,
                remote=remote,
                required=False,
                noop_reason=".pre-commit-config.yaml absent — lint ensure would fail",
            )
        )

    return tuple(steps)


def build_image_layer_plan_steps_for_runtime(
    runtime: RuntimePorts,
) -> tuple[PlanStep, ...]:
    return build_image_layer_plan_steps(
        runtime.bootstrap, runtime.host_ctx, runtime.args
    )
