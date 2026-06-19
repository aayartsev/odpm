"""Tests for odpm manifest CLI subcommands."""

from __future__ import annotations

import json
import tempfile
import unittest
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.host.cli.parse_args import parse_cli_args
from dev_project.manifest.commands import run_manifest_command
from dev_project.plan.cli import is_manifest_mode


class ManifestCliArgsTests(unittest.TestCase):
    def test_parse_manifest_migrate(self):
        cli_args = parse_cli_args(["manifest", "migrate"])
        self.assertEqual(cli_args.command, "manifest")
        self.assertEqual(cli_args.manifest_subcommand, "migrate")
        self.assertFalse(cli_args.manifest_migrate_write)
        self.assertTrue(is_manifest_mode(cli_args))

    def test_parse_manifest_migrate_write(self):
        cli_args = parse_cli_args(["manifest", "migrate", "--write"])
        self.assertTrue(cli_args.manifest_migrate_write)


class ManifestMigrateCommandTests(unittest.TestCase):
    def test_migrate_prints_diff_without_write(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = f"{tmp}/developing/odpm.json"
            import os

            os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
            v1 = {
                "odpm_version": constants.MANIFEST_V1_CONTRACT_LINE,
                "odoo_version": "17.0",
                "python_version": "3.12",
                "distro_name": "debian",
                "distro_version": "12",
                "postgres_version": "16",
                "odoo_git_link": "https://github.com/odoo/odoo.git 17.0",
                "dependencies": [],
                "requirements_txt": [],
            }
            with open(manifest_path, "w", encoding="utf-8") as handle:
                json.dump(v1, handle)

            config = MagicMock()
            config.repo_odpm_json = manifest_path
            config.project_dir = tmp
            config.bootstrap.raw_user_settings = {}

            cli_args = parse_cli_args(["manifest", "migrate"])
            with patch("builtins.print") as print_mock:
                code = run_manifest_command(cli_args, config)

            self.assertEqual(code, 0)
            print_mock.assert_called_once()
            diff_text = print_mock.call_args.args[0]
            self.assertIn("manifest_schema", diff_text)
            with open(manifest_path, encoding="utf-8") as handle:
                on_disk = json.load(handle)
            self.assertNotIn("manifest_schema", on_disk)

    def test_migrate_write_updates_manifest(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest_path = f"{tmp}/developing/odpm.json"
            import os

            os.makedirs(os.path.dirname(manifest_path), exist_ok=True)
            v1 = {
                "odpm_version": constants.MANIFEST_V1_CONTRACT_LINE,
                "odoo_version": "17.0",
                "python_version": "3.12",
                "distro_name": "debian",
                "distro_version": "12",
                "postgres_version": "16",
                "odoo_git_link": "https://github.com/odoo/odoo.git 17.0",
                "dependencies": [],
                "requirements_txt": [],
            }
            with open(manifest_path, "w", encoding="utf-8") as handle:
                json.dump(v1, handle)

            config = MagicMock()
            config.repo_odpm_json = manifest_path
            config.project_dir = tmp
            config.bootstrap.raw_user_settings = {}

            cli_args = parse_cli_args(["manifest", "migrate", "--write"])
            code = run_manifest_command(cli_args, config)

            self.assertEqual(code, 0)
            with open(manifest_path, encoding="utf-8") as handle:
                on_disk = json.load(handle)
            self.assertEqual(on_disk["manifest_schema"], 2)


if __name__ == "__main__":
    unittest.main()
