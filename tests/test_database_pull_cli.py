"""Tests for odpm database pull."""

from __future__ import annotations

import io
import os
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project.database.commands import REMOTE_DB_MASTER_PWD_ENV, _run_database_pull
from dev_project.errors import ConfigError
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.host.cli.parse_args import parse_cli_args


def _zip_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("dump.sql", "SELECT 1;\n")
    return buf.getvalue()


class DatabasePullCliTests(unittest.TestCase):
    def test_parse_pull(self):
        args = parse_cli_args(
            [
                "database",
                "pull",
                "--url",
                "https://client.example.com",
                "--remote-db",
                "prod",
            ]
        )
        self.assertEqual(args.command, "database")
        self.assertEqual(args.database_subcommand, "pull")
        self.assertEqual(args.database_pull_url, "https://client.example.com")
        self.assertEqual(args.database_pull_remote_db, "prod")

    def test_pull_requires_env_password(self):
        config = MagicMock()
        config.user_env.backups = "/tmp/backups"
        args = OdpmCliArgs(
            command="database",
            database_subcommand="pull",
            database_pull_url="https://client.example.com",
            database_pull_remote_db="prod",
        )
        env = {k: v for k, v in os.environ.items() if k != REMOTE_DB_MASTER_PWD_ENV}
        with patch.dict(os.environ, env, clear=True):
            with self.assertRaises(ConfigError) as ctx:
                _run_database_pull(args, config)
            self.assertIn(REMOTE_DB_MASTER_PWD_ENV, str(ctx.exception))

    def test_pull_writes_archive_and_prints_name(self):
        payload = _zip_bytes()

        def fake_download(url, dest_path, fields, **kwargs):
            self.assertIn("/web/database/backup", url)
            self.assertEqual(fields["name"], "prod")
            self.assertEqual(fields["master_pwd"], "secret")
            path = Path(dest_path)
            path.write_bytes(payload)
            return path

        with tempfile.TemporaryDirectory() as tmp:
            config = MagicMock()
            config.user_env.backups = tmp
            args = OdpmCliArgs(
                command="database",
                database_subcommand="pull",
                database_pull_url="https://client.example.com",
                database_pull_remote_db="prod",
            )
            with patch.dict(os.environ, {REMOTE_DB_MASTER_PWD_ENV: "secret"}):
                with patch(
                    "dev_project.database.commands.download_multipart_post",
                    side_effect=fake_download,
                ):
                    with patch("sys.stdout", new_callable=io.StringIO) as out:
                        code = _run_database_pull(args, config)
            self.assertEqual(code, 0)
            name = out.getvalue().strip()
            self.assertTrue(name.endswith(".zip"))
            self.assertTrue((Path(tmp) / name).is_file())
            self.assertIn("client_example_com", name)
            self.assertIn("prod", name)


if __name__ == "__main__":
    unittest.main()
