"""Secrets fetch and materialize prepare steps."""

from __future__ import annotations

import os

from .. import constants
from ..plan import PlanStep
from ..plan.l10n import plan_msg
from ..plan.secrets_preview import secrets_needs_update, secrets_source_key_count
from ..project_env.secrets import materialize_secrets
from ..secrets_providers.resolve import resolve_secrets_provider_name
from ..secrets_providers.session import session_for_config
from .helpers import make_plan_step
from .types import PrepareContext


def _provider_name_for_ctx(ctx: PrepareContext) -> str:
    spec = None
    if ctx.manifest_view is not None and ctx.manifest_view.scenario_slice is not None:
        spec = ctx.manifest_view.scenario_slice.secrets
    manifest_type = spec.provider.type if spec is not None and spec.provider else None
    environ: dict[str, str] = {}
    user_env = getattr(ctx.host_ctx, "user_env", None)
    getter = getattr(user_env, "project_dotenv_dict", None)
    if callable(getter):
        dotenv = getter()
        if isinstance(dotenv, dict):
            environ.update({str(k): str(v) for k, v in dotenv.items()})
    environ.update({str(k): str(v) for k, v in os.environ.items()})
    return resolve_secrets_provider_name(ctx.args, environ, manifest_type)


def evaluate_secrets_fetch(ctx: PrepareContext) -> PlanStep:
    provider_name = _provider_name_for_ctx(ctx)
    session = session_for_config(ctx.ports.bootstrap.config)
    description = plan_msg(
        "Fetch secrets via provider {NAME}"
    ).format(NAME=provider_name)

    if provider_name == constants.SECRETS_PROVIDER_FILE:
        if ctx.args.secrets_file:
            if session.fetched:
                return make_plan_step(
                    "secrets.fetch",
                    description,
                    "skip",
                    True,
                    plan_msg("secrets already imported this run"),
                )
            return make_plan_step(
                "secrets.fetch",
                description,
                "update",
                True,
                plan_msg("import --secrets-file"),
            )
        return make_plan_step(
            "secrets.fetch",
            description,
            "skip",
            True,
            plan_msg("file provider uses existing source"),
        )

    if session.fetched:
        count = session.key_count or secrets_source_key_count(ctx.host_ctx.project_dir)
        return make_plan_step(
            "secrets.fetch",
            description,
            "noop",
            True,
            plan_msg("already fetched this run ({COUNT} keys)").format(COUNT=count),
        )
    return make_plan_step(
        "secrets.fetch",
        description,
        "update",
        True,
        plan_msg("remote provider configured"),
    )


def exec_secrets_fetch(ctx: PrepareContext) -> None:
    from ..secrets_providers.fetch import ensure_secrets_source_for_config

    raw = {}
    view = ctx.manifest_view
    if view is not None and getattr(view, "source_raw", None):
        raw = dict(view.source_raw)
    elif view is not None and getattr(view, "raw_normalized", None):
        raw = dict(view.raw_normalized)
    ensure_secrets_source_for_config(ctx.ports.bootstrap.config, raw=raw, phase="prepare")


def evaluate_secrets_materialize(ctx: PrepareContext) -> PlanStep:
    description = plan_msg(
        "Materialize .odpm/runtime/secrets.json from .odpm/secrets.json"
    )
    if not ctx.host_ctx.policy.mount_runtime_secrets_from_host():
        return make_plan_step(
            "secrets.materialize",
            description,
            "skip",
            True,
            plan_msg("secrets mount disabled for CI scenario"),
        )
    needs_update, reason = secrets_needs_update(ctx.host_ctx.project_dir)
    if needs_update:
        return make_plan_step(
            "secrets.materialize",
            description,
            "update",
            True,
            plan_msg(reason),
        )
    return make_plan_step(
        "secrets.materialize",
        description,
        "noop",
        True,
        plan_msg(reason),
    )


def exec_secrets_materialize(ctx: PrepareContext) -> None:
    if not ctx.host_ctx.policy.mount_runtime_secrets_from_host():
        return
    materialize_secrets(ctx.host_ctx.project_dir)
