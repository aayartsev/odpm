"""Tests for the file secrets provider."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from dev_project.host.cli.args import OdpmCliArgs
from dev_project.project_env.secrets import read_secrets_source, write_secrets_source
from dev_project.secrets_providers.file_provider import FileSecretsProvider


class FileSecretsProviderTests(unittest.TestCase):
    def test_imports_secrets_file(self):
        with tempfile.TemporaryDirectory() as project_dir:
            external = Path(project_dir) / "in.json"
            external.write_text(
                json.dumps({"schema_version": 1, "secrets": {"a": "1"}}),
                encoding="utf-8",
            )
            os.chmod(external, 0o600)
            provider = FileSecretsProvider()
            secrets = provider.fetch(
                provider_config={},
                credentials={},
                project_dir=project_dir,
                arguments=OdpmCliArgs(secrets_file=str(external)),
            )
            self.assertEqual(secrets, {"a": "1"})
            self.assertEqual(read_secrets_source(project_dir), {"a": "1"})

    def test_returns_existing_source_without_flag(self):
        with tempfile.TemporaryDirectory() as project_dir:
            write_secrets_source(project_dir, {"token": "x"})
            secrets = FileSecretsProvider().fetch(
                provider_config={},
                credentials={},
                project_dir=project_dir,
                arguments=OdpmCliArgs(),
            )
            self.assertEqual(secrets, {"token": "x"})

    def test_missing_source_returns_empty(self):
        with tempfile.TemporaryDirectory() as project_dir:
            secrets = FileSecretsProvider().fetch(
                provider_config={},
                credentials={},
                project_dir=project_dir,
                arguments=OdpmCliArgs(),
            )
            self.assertEqual(secrets, {})


if __name__ == "__main__":
    unittest.main()
