"""Tests for odpm CLI subcommand normalize / compatibility shim (4.8)."""

from __future__ import annotations

import unittest

from dev_project.host.cli.args import OdpmCliArgs
from dev_project.host.cli.normalize import CliNormalizeError, normalize_cli_args
from dev_project.host.cli.parse_args import parse_args, parse_cli_args
from dev_project.plan.cli import (
    is_database_host_mode,
    is_database_stack_mode,
    is_prepare_mode,
    is_scaffold_mode,
    is_up_mode,
)
from dev_project.system_check_policy import cli_allows_ci_explicit_mode


class NormalizeCliArgsTests(unittest.TestCase):
    def test_bare_maps_to_up(self):
        args, warning = normalize_cli_args(OdpmCliArgs())
        self.assertEqual(args.command, "up")
        self.assertIn("odpm up", warning or "")
        self.assertIn("5.0", warning or "")

    def test_skip_start_maps_to_prepare(self):
        args, warning = normalize_cli_args(OdpmCliArgs(skip_start=True))
        self.assertEqual(args.command, "prepare")
        self.assertTrue(args.skip_start)
        self.assertIn("prepare", warning or "")

    def test_init_flag_maps_to_init(self):
        args, warning = normalize_cli_args(OdpmCliArgs(init="https://example.com/r.git"))
        self.assertEqual(args.command, "init")
        self.assertIn("odpm init", warning or "")

    def test_build_image_maps_to_build(self):
        args, warning = normalize_cli_args(OdpmCliArgs(build_image=True))
        self.assertEqual(args.command, "build")
        self.assertTrue(args.build_image)

    def test_single_db_restore_maps_to_database(self):
        args, warning = normalize_cli_args(OdpmCliArgs(db_restore="a.zip", d="db1"))
        self.assertEqual(args.command, "database")
        self.assertEqual(args.database_subcommand, "restore")
        self.assertEqual(args.db_restore, "a.zip")
        self.assertIsNotNone(warning)

    def test_db_restore_with_i_maps_to_up(self):
        args, warning = normalize_cli_args(
            OdpmCliArgs(db_restore="a.zip", d="db1", i="sale")
        )
        self.assertEqual(args.command, "up")
        self.assertEqual(args.db_restore, "a.zip")
        self.assertEqual(args.i, "sale")

    def test_multi_stack_flags_map_to_up(self):
        args, _warning = normalize_cli_args(
            OdpmCliArgs(db_drop=True, db_restore="a.zip", d="db1")
        )
        self.assertEqual(args.command, "up")
        self.assertTrue(args.db_drop)
        self.assertEqual(args.db_restore, "a.zip")

    def test_reject_skip_start_with_db_restore(self):
        with self.assertRaises(CliNormalizeError):
            normalize_cli_args(OdpmCliArgs(skip_start=True, db_restore="a.zip"))

    def test_reject_init_with_db_backup(self):
        with self.assertRaises(CliNormalizeError):
            normalize_cli_args(
                OdpmCliArgs(init="https://example.com/r.git", db_backup=True)
            )

    def test_reject_build_with_db_drop(self):
        with self.assertRaises(CliNormalizeError):
            normalize_cli_args(OdpmCliArgs(build_image=True, db_drop=True))

    def test_version_not_mapped_to_up(self):
        args, warning = normalize_cli_args(OdpmCliArgs(version=True))
        self.assertTrue(args.version)
        self.assertIsNone(args.command)
        self.assertIsNone(warning)

    def test_explicit_prepare_sets_skip_start(self):
        args, warning = normalize_cli_args(OdpmCliArgs(command="prepare"))
        self.assertTrue(args.skip_start)
        self.assertIsNone(warning)

    def test_stack_restore_rejects_module_flags(self):
        with self.assertRaises(CliNormalizeError):
            normalize_cli_args(
                OdpmCliArgs(
                    command="database",
                    database_subcommand="restore",
                    db_restore="a.zip",
                    d="db1",
                    i="sale",
                )
            )


class ParseCliArgsTests(unittest.TestCase):
    def test_parse_version_short(self):
        args = parse_cli_args(["-V"])
        self.assertTrue(args.version)
        self.assertIsNone(args.command)

    def test_parse_version_long(self):
        args = parse_cli_args(["--version"])
        self.assertTrue(args.version)

    def test_parse_v_lowercase_not_version(self):
        with self.assertRaises(SystemExit):
            parse_args(["-v"])

    def test_parse_up(self):
        args = parse_cli_args(["up", "-d", "demo", "-i", "sale"])
        self.assertEqual(args.command, "up")
        self.assertEqual(args.d, "demo")
        self.assertEqual(args.i, "sale")

    def test_parse_database_backup(self):
        args = parse_cli_args(["database", "backup", "-d", "demo"])
        self.assertTrue(is_database_stack_mode(args))
        self.assertFalse(is_database_host_mode(args))
        self.assertEqual(args.db_backup, True)

    def test_parse_database_status_host(self):
        args = parse_cli_args(["database", "status"])
        self.assertTrue(is_database_host_mode(args))
        self.assertFalse(is_database_stack_mode(args))

    def test_leakage_before_database_status(self):
        with self.assertRaises(SystemExit):
            parse_cli_args(["-i", "sale", "database", "status"])

    def test_database_restore_rejects_i_on_parser(self):
        with self.assertRaises(SystemExit):
            parse_args(["database", "restore", "-d", "x", "a.zip", "-i", "sale"])

    def test_modes(self):
        self.assertTrue(is_up_mode(parse_cli_args(["up"])))
        self.assertTrue(is_prepare_mode(parse_cli_args(["prepare"])))
        self.assertTrue(is_scaffold_mode(OdpmCliArgs(command="scaffold")))


class CiAllowlistTests(unittest.TestCase):
    def test_ci_matrix(self):
        self.assertTrue(
            cli_allows_ci_explicit_mode(
                OdpmCliArgs(command="prepare", skip_start=True)
            )
        )
        self.assertTrue(
            cli_allows_ci_explicit_mode(
                OdpmCliArgs(command="database", database_subcommand="status")
            )
        )
        self.assertTrue(cli_allows_ci_explicit_mode(OdpmCliArgs(version=True)))
        self.assertFalse(cli_allows_ci_explicit_mode(OdpmCliArgs(command="up")))
        self.assertFalse(
            cli_allows_ci_explicit_mode(
                OdpmCliArgs(command="database", database_subcommand="backup")
            )
        )
        self.assertFalse(cli_allows_ci_explicit_mode(OdpmCliArgs(command="scaffold")))
        self.assertFalse(cli_allows_ci_explicit_mode(OdpmCliArgs(command="database")))


class SetupForPlanHostVsStackTests(unittest.TestCase):
    def test_host_database_uses_lightweight_setup_flag(self):
        host = parse_cli_args(["database", "status"])
        stack = parse_cli_args(["database", "backup", "-d", "demo"])
        self.assertTrue(is_database_host_mode(host))
        self.assertTrue(is_database_stack_mode(stack))
        # Mirror pipeline condition for for_plan=
        self.assertTrue(is_database_host_mode(host))
        self.assertFalse(is_database_host_mode(stack))


if __name__ == "__main__":
    unittest.main()
