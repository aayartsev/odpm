"""Tests for typed host CLI arguments (OdpmCliArgs)."""

from __future__ import annotations

import unittest
from argparse import Namespace

import dev_project.host_cli.parse_args as parse_args_module
from dev_project.host_cli.args import OdpmCliArgs, as_cli_args
from dev_project.host_cli.parse_args import parse_cli_args
from dev_project.plan_cli import is_plan_mode


class OdpmCliArgsBridgeTests(unittest.TestCase):
    def test_from_namespace_reads_known_fields(self):
        ns = Namespace(plan=True, skip_start=True, plan_strict=True, d="demo")
        cli_args = OdpmCliArgs.from_namespace(ns)
        self.assertTrue(cli_args.plan)
        self.assertTrue(cli_args.skip_start)
        self.assertTrue(cli_args.plan_strict)
        self.assertEqual(cli_args.d, "demo")
        self.assertFalse(cli_args.build_image)

    def test_from_namespace_uses_defaults_for_missing_fields(self):
        cli_args = OdpmCliArgs.from_namespace(Namespace())
        self.assertEqual(cli_args.plan_format, "table")
        self.assertEqual(cli_args.requirements_txt, "")
        self.assertFalse(cli_args.plan)

    def test_to_namespace_round_trip(self):
        original = parse_args_module.parse_args(
            ["plan", "--skip-start", "--plan-format", "json", "--plan-strict"]
        )
        restored = OdpmCliArgs.from_namespace(original).to_namespace()
        original_vars = vars(original)
        restored_vars = {key: value for key, value in vars(restored).items() if key in original_vars}
        self.assertEqual(restored_vars, original_vars)

    def test_to_namespace_includes_scaffold_fields_when_present(self):
        original = parse_args_module.parse_args(["scaffold", "mymod", "-t", "default"])
        restored = OdpmCliArgs.from_namespace(original).to_namespace()
        self.assertEqual(restored.scaffold_module_name, "mymod")
        self.assertEqual(restored.scaffold_template_name, "default")

    def test_as_cli_args_passthrough(self):
        cli_args = OdpmCliArgs(plan=True, skip_start=True)
        self.assertIs(as_cli_args(cli_args), cli_args)

    def test_as_cli_args_from_namespace(self):
        cli_args = as_cli_args(Namespace(plan=True))
        self.assertTrue(cli_args.plan)

    def test_parse_cli_args_matches_parse_args_namespace(self):
        argv = ["plan", "--skip-start", "--no-git-update"]
        ns = parse_args_module.parse_args(argv)
        cli_args = parse_cli_args(argv)
        ns_vars = vars(ns)
        restored_vars = {
            key: value for key, value in vars(cli_args.to_namespace()).items() if key in ns_vars
        }
        self.assertEqual(restored_vars, ns_vars)

    def test_is_plan_mode_accepts_odpm_cli_args(self):
        self.assertTrue(is_plan_mode(OdpmCliArgs(plan=True)))
        self.assertFalse(is_plan_mode(OdpmCliArgs()))


if __name__ == "__main__":
    unittest.main()
