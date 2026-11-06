"""Host CLI subparser for odpm image <layer> ensure."""

from __future__ import annotations

import argparse

from . import params


def register_image_subparser(
    command_subparsers,
    global_parser: argparse.ArgumentParser,
) -> argparse.ArgumentParser:
    parser = command_subparsers.add_parser(
        params.IMAGE_SUBCOMMAND,
        parents=[global_parser],
        help=(
            "Ensure a layered CI image stage. "
            "Example: odpm image platform ensure --image-push"
        ),
        description=(
            "Idempotent layered CI image stages (ADR-027): "
            "base, platform, deps, app, lint. "
            "Families in registry tags: dev (profile full) and runtime (profile medium)."
        ),
    )
    layer_subparsers = parser.add_subparsers(
        dest="image_layer",
        help="Image layer",
        required=True,
    )
    for layer in (
        params.IMAGE_BASE_LAYER,
        params.IMAGE_PLATFORM_LAYER,
        params.IMAGE_DEPS_LAYER,
        params.IMAGE_APP_LAYER,
        params.IMAGE_LINT_LAYER,
    ):
        layer_parser = layer_subparsers.add_parser(
            layer,
            help=f"Operate on the {layer} layer",
        )
        action_subparsers = layer_parser.add_subparsers(
            dest="image_action",
            help="Layer action",
            required=True,
        )
        ensure_parser = action_subparsers.add_parser(
            params.IMAGE_ENSURE_SUBCOMMAND,
            help=f"Ensure the {layer} image (build/push if missing)",
        )
        ensure_parser.set_defaults(image_ensure=True)
        ensure_parser.add_argument(
            params.IMAGE_TAG_PARAM,
            help="Image tag / destination ref (required for app when pushing)",
            type=str,
        )
        ensure_parser.add_argument(
            params.IMAGE_BUILDER_PARAM,
            help="Image build backend: docker (default) or kaniko",
            choices=["docker", "kaniko"],
            type=str,
        )
        ensure_parser.add_argument(
            params.IMAGE_PUSH_PARAM,
            help="Push the image after build",
            action="store_true",
        )
        if layer != params.IMAGE_BASE_LAYER:
            ensure_parser.add_argument(
                params.IMAGE_PRUNE_STALE_PARAM,
                dest="image_prune_stale",
                help=(
                    "After successful ensure, delete stale cache-* tags for "
                    "this layer (same family/version/build_date, other "
                    "fingerprint); also ODPM_IMAGE_PRUNE_STALE=1"
                ),
                action="store_true",
            )
        ensure_parser.add_argument(
            params.NO_GIT_UPDATE_PARAM,
            help="Skip git clone/fetch/checkout when sources already exist",
            action="store_true",
        )
        if layer in {params.IMAGE_APP_LAYER, params.IMAGE_DEPS_LAYER}:
            ensure_parser.add_argument(
                params.IMAGE_FROM_PARAM,
                dest="image_from",
                help="Parent image ref (default: resolved platform or deps ref)",
                type=str,
            )
    return parser
