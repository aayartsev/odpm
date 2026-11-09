"""CLI parse / allowlist for odpm image and prepare --stop-after sources."""

from __future__ import annotations

import unittest

import dev_project.host.cli.parse_args as parse_args_module
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.host.cli import params
from dev_project.host.cli.parse_args import parse_cli_args
from dev_project.plan.cli import is_image_mode
from dev_project.prepare.sources_only import (
    IMAGE_ENSURE_STEP_IDS,
    SOURCES_ONLY_STEP_IDS,
    is_image_ensure_prepare,
    is_sources_only_prepare,
)
from dev_project.system_check_policy import cli_allows_ci_explicit_mode


class ImageCliParseTests(unittest.TestCase):
    def test_parse_image_platform_ensure(self):
        args = parse_cli_args(
            ["image", "platform", "ensure", "--image-push", "--image-builder", "kaniko"]
        )
        self.assertEqual(args.command, params.IMAGE_SUBCOMMAND)
        self.assertEqual(args.image_layer, params.IMAGE_PLATFORM_LAYER)
        self.assertTrue(args.image_ensure)
        self.assertTrue(args.image_push)
        self.assertEqual(args.image_builder, "kaniko")
        self.assertTrue(is_image_mode(args))
        self.assertFalse(args.image_prune_stale)

    def test_parse_image_app_ensure_prune_stale(self):
        args = parse_cli_args(
            ["image", "app", "ensure", "--image-prune-stale"]
        )
        self.assertEqual(args.image_layer, params.IMAGE_APP_LAYER)
        self.assertTrue(args.image_prune_stale)

    def test_parse_build_prune_stale(self):
        args = parse_cli_args(["build", "--image-prune-stale", "--image-tag", "x:y"])
        self.assertEqual(args.command, params.BUILD_SUBCOMMAND)
        self.assertTrue(args.image_prune_stale)
        self.assertEqual(args.image_tag, "x:y")

    def test_image_base_ensure_rejects_prune_flag(self):
        with self.assertRaises(SystemExit):
            parse_args_module.parse_args(
                ["image", "base", "ensure", "--image-prune-stale"]
            )

    def test_parse_image_app_ensure_from(self):
        args = parse_cli_args(
            [
                "image",
                "app",
                "ensure",
                "--from",
                "reg/proj:cache-platform-x",
                "--image-tag",
                "reg/proj:final",
            ]
        )
        self.assertEqual(args.image_layer, params.IMAGE_APP_LAYER)
        self.assertEqual(args.image_from, "reg/proj:cache-platform-x")
        self.assertEqual(args.image_tag, "reg/proj:final")

    def test_parse_image_all_layers(self):
        for layer in params.IMAGE_LAYERS:
            with self.subTest(layer=layer):
                ns = parse_args_module.parse_args(["image", layer, "ensure"])
                self.assertEqual(ns.image_layer, layer)
                self.assertTrue(getattr(ns, "image_ensure", False))

    def test_parse_prepare_stop_after_sources(self):
        args = parse_cli_args(["prepare", "--stop-after", "sources"])
        self.assertEqual(args.command, params.PREPARE_SUBCOMMAND)
        self.assertEqual(args.stop_after, params.STOP_AFTER_SOURCES)
        self.assertTrue(is_sources_only_prepare(args.stop_after))

    def test_ci_allowlist_includes_image(self):
        self.assertTrue(
            cli_allows_ci_explicit_mode(
                OdpmCliArgs(command=params.IMAGE_SUBCOMMAND, image_layer="platform")
            )
        )
        self.assertFalse(
            cli_allows_ci_explicit_mode(OdpmCliArgs(command=params.UP_SUBCOMMAND))
        )
        self.assertFalse(
            cli_allows_ci_explicit_mode(OdpmCliArgs(d="db", i="sale"))
        )

    def test_sources_only_whitelist_excludes_docker(self):
        self.assertIn("git.materialize_developing", SOURCES_ONLY_STEP_IDS)
        self.assertIn("git.materialize_platform", SOURCES_ONLY_STEP_IDS)
        self.assertIn("git.materialize_dependencies", SOURCES_ONLY_STEP_IDS)
        self.assertNotIn("git.materialize", SOURCES_ONLY_STEP_IDS)
        self.assertIn("sources.materialize", SOURCES_ONLY_STEP_IDS)
        self.assertNotIn("docker.engine_check", SOURCES_ONLY_STEP_IDS)
        self.assertNotIn("compose.validate", SOURCES_ONLY_STEP_IDS)
        self.assertNotIn("secrets.materialize", SOURCES_ONLY_STEP_IDS)

    def test_image_ensure_prepare_includes_secrets(self):
        self.assertTrue(SOURCES_ONLY_STEP_IDS <= IMAGE_ENSURE_STEP_IDS)
        self.assertIn("secrets.fetch", IMAGE_ENSURE_STEP_IDS)
        self.assertIn("secrets.materialize", IMAGE_ENSURE_STEP_IDS)
        self.assertIn("template.dockerfile", IMAGE_ENSURE_STEP_IDS)
        self.assertIn("template.dockerignore", IMAGE_ENSURE_STEP_IDS)
        self.assertNotIn("template.odoo_conf", IMAGE_ENSURE_STEP_IDS)
        self.assertNotIn("docker.engine_check", IMAGE_ENSURE_STEP_IDS)
        self.assertNotIn("compose.validate", IMAGE_ENSURE_STEP_IDS)
        args = OdpmCliArgs(command=params.IMAGE_SUBCOMMAND, image_layer="app")
        self.assertTrue(is_image_ensure_prepare(args))
        self.assertFalse(
            is_image_ensure_prepare(
                OdpmCliArgs(
                    command=params.IMAGE_SUBCOMMAND,
                    stop_after=params.STOP_AFTER_SOURCES,
                )
            )
        )
        self.assertFalse(
            is_image_ensure_prepare(OdpmCliArgs(command=params.PREPARE_SUBCOMMAND))
        )


if __name__ == "__main__":
    unittest.main()
