"""Tests for typed host CLI arguments (OdpmCliArgs)."""

from __future__ import annotations

import unittest
from argparse import Namespace

import dev_project.host.cli.parse_args as parse_args_module
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.host.cli.parse_args import parse_cli_args
from dev_project.plan.cli import is_plan_mode


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

    def test_from_namespace_round_trip_fields(self):
        original = parse_args_module.parse_args(
            ["plan", "--skip-start", "--plan-format", "json", "--plan-strict"]
        )
        cli_args = OdpmCliArgs.from_namespace(original)
        self.assertTrue(cli_args.plan)
        self.assertTrue(cli_args.skip_start)
        self.assertEqual(cli_args.plan_format, "json")
        self.assertTrue(cli_args.plan_strict)
        self.assertEqual(cli_args.command, "plan")

    def test_from_namespace_reads_scaffold_fields(self):
        original = parse_args_module.parse_args(["scaffold", "mymod", "-t", "default"])
        cli_args = OdpmCliArgs.from_namespace(original)
        self.assertEqual(cli_args.scaffold_module_name, "mymod")
        self.assertEqual(cli_args.scaffold_template_name, "default")

    def test_from_namespace_reads_database_fields(self):
        original = parse_args_module.parse_args(["database", "status", "--format", "json"])
        cli_args = OdpmCliArgs.from_namespace(original)
        self.assertEqual(cli_args.command, "database")
        self.assertEqual(cli_args.database_subcommand, "status")
        self.assertEqual(cli_args.database_status_format, "json")

    def test_from_namespace_reads_accept_database_drift(self):
        original = parse_args_module.parse_args(
            ["--accept-database-drift", "data_path", "--accept-database-drift", "app_role_missing"]
        )
        cli_args = OdpmCliArgs.from_namespace(original)
        self.assertEqual(
            cli_args.accept_database_drift,
            ("data_path", "app_role_missing"),
        )

    def test_parse_cli_args_matches_parse_args(self):
        argv = ["plan", "--skip-start", "--no-git-update"]
        ns = parse_args_module.parse_args(argv)
        cli_args = parse_cli_args(argv)
        self.assertEqual(cli_args, OdpmCliArgs.from_namespace(ns))

    def test_is_plan_mode_accepts_odpm_cli_args(self):
        self.assertTrue(is_plan_mode(OdpmCliArgs(plan=True)))
        self.assertTrue(is_plan_mode(OdpmCliArgs(command="plan")))
        self.assertFalse(is_plan_mode(OdpmCliArgs()))


if __name__ == "__main__":
    unittest.main()
