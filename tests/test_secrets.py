import json
import os
import stat
import tempfile
import unittest
from pathlib import Path

from dev_project import constants
from dev_project.errors import ConfigError
from dev_project.host.cli.parse_args import parse_cli_args
from dev_project.project_env.secrets import (
    ensure_secrets_gitignore,
    import_secrets_from_path,
    materialize_secrets,
    read_secrets_source,
    secrets_runtime_path,
    secrets_source_is_gitignored,
    secrets_source_path,
    validate_secrets_file,
)


class SecretsModuleTests(unittest.TestCase):
    def _write_json(self, path: str, payload: dict) -> None:
        Path(path).write_text(json.dumps(payload), encoding="utf-8")

    def test_validate_secrets_file_accepts_schema_v1(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "secrets.json")
            self._write_json(
                path,
                {
                    "schema_version": 1,
                    "secrets": {"payment.api_key": "sk_test"},
                },
            )
            secrets = validate_secrets_file(path)
            self.assertEqual(secrets, {"payment.api_key": "sk_test"})

    def test_validate_rejects_non_string_values(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "secrets.json")
            self._write_json(
                path,
                {"schema_version": 1, "secrets": {"key": 123}},
            )
            with self.assertRaises(ConfigError):
                validate_secrets_file(path)

    def test_import_copies_external_file_to_source(self):
        with tempfile.TemporaryDirectory() as project_dir:
            external = os.path.join(project_dir, "external.json")
            self._write_json(
                external,
                {"schema_version": 1, "secrets": {"a": "1"}},
            )
            destination = import_secrets_from_path(project_dir, external)
            self.assertEqual(destination, secrets_source_path(project_dir))
            self.assertEqual(read_secrets_source(project_dir), {"a": "1"})
            mode = stat.S_IMODE(os.stat(destination).st_mode)
            self.assertEqual(mode, 0o600)

    def test_import_same_path_revalidates_without_error(self):
        with tempfile.TemporaryDirectory() as project_dir:
            source = secrets_source_path(project_dir)
            os.makedirs(os.path.dirname(source), exist_ok=True)
            self._write_json(
                source,
                {"schema_version": 1, "secrets": {"token": "x"}},
            )
            returned = import_secrets_from_path(project_dir, source)
            self.assertEqual(returned, source)
            self.assertEqual(read_secrets_source(project_dir), {"token": "x"})

    def test_materialize_writes_runtime_and_noop_when_unchanged(self):
        with tempfile.TemporaryDirectory() as project_dir:
            import_secrets_from_path(
                project_dir,
                self._create_external(project_dir, {"k": "v"}),
            )
            self.assertTrue(materialize_secrets(project_dir))
            runtime = secrets_runtime_path(project_dir)
            self.assertTrue(os.path.isfile(runtime))
            first = Path(runtime).read_text(encoding="utf-8")
            self.assertTrue(materialize_secrets(project_dir))
            second = Path(runtime).read_text(encoding="utf-8")
            self.assertEqual(first, second)

    def test_materialize_removes_stale_runtime_when_source_missing(self):
        with tempfile.TemporaryDirectory() as project_dir:
            import_secrets_from_path(
                project_dir,
                self._create_external(project_dir, {"k": "v"}),
            )
            materialize_secrets(project_dir)
            runtime = secrets_runtime_path(project_dir)
            self.assertTrue(os.path.isfile(runtime))
            os.remove(secrets_source_path(project_dir))
            self.assertFalse(materialize_secrets(project_dir))
            self.assertFalse(os.path.isfile(runtime))

    def test_cli_parses_secrets_file_flag(self):
        args = parse_cli_args(["--secrets-file", "/tmp/secrets.json", "--skip-start"])
        self.assertEqual(args.secrets_file, "/tmp/secrets.json")

    def test_ensure_secrets_gitignore_adds_entry(self):
        with tempfile.TemporaryDirectory() as project_dir:
            ensure_secrets_gitignore(project_dir)
            self.assertTrue(secrets_source_is_gitignored(project_dir))

    def _create_external(self, project_dir: str, secrets: dict[str, str]) -> str:
        path = os.path.join(project_dir, "incoming.json")
        self._write_json(path, {"schema_version": 1, "secrets": secrets})
        return path


if __name__ == "__main__":
    unittest.main()
