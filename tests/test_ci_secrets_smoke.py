"""CI secrets import smoke (TD-FEAT-09 MVP): --secrets-file → materialize → compose."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.prepare import make_prepare_context
from dev_project.prepare.steps_secrets import evaluate_secrets_materialize
from dev_project.project_env.secrets import (
    import_secrets_from_path,
    materialize_secrets,
    secrets_runtime_path,
    secrets_source_path,
)
from dev_project.scenario_policy import ScenarioPolicy
from tests.fixtures.minimal_odpm_fixture import provision_minimal_odpm_project
from tests.plan_smoke_helpers import repo_root


class CiSecretsPreparePolicyTests(unittest.TestCase):
    def _external_secrets(self, directory: str) -> str:
        path = os.path.join(directory, "ci-secrets.json")
        Path(path).write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "secrets": {"ci.smoke_key": "from_actions"},
                }
            ),
            encoding="utf-8",
        )
        os.chmod(path, 0o600)
        return path

    def test_import_and_materialize_writes_runtime_json(self):
        with tempfile.TemporaryDirectory() as project_dir:
            external = self._external_secrets(project_dir)
            import_secrets_from_path(project_dir, external)
            self.assertTrue(os.path.isfile(secrets_source_path(project_dir)))
            self.assertTrue(materialize_secrets(project_dir))
            runtime_path = secrets_runtime_path(project_dir)
            self.assertTrue(os.path.isfile(runtime_path))
            payload = json.loads(Path(runtime_path).read_text(encoding="utf-8"))
            self.assertEqual(payload["secrets"]["ci.smoke_key"], "from_actions")

    def test_prepare_step_updates_for_developer(self):
        with tempfile.TemporaryDirectory() as project_dir:
            import_secrets_from_path(project_dir, self._external_secrets(project_dir))
            config = MagicMock()
            config.project_dir = project_dir
            config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
            ctx = make_prepare_context(
                config, MagicMock(), MagicMock(), OdpmCliArgs()
            )
            step = evaluate_secrets_materialize(ctx)
            self.assertEqual(step.id, "secrets.materialize")
            self.assertEqual(step.outcome, "update")

    def test_prepare_step_skips_for_ci(self):
        with tempfile.TemporaryDirectory() as project_dir:
            import_secrets_from_path(project_dir, self._external_secrets(project_dir))
            config = MagicMock()
            config.project_dir = project_dir
            config.policy = ScenarioPolicy.from_scenario(constants.CI_SCENARIO)
            ctx = make_prepare_context(
                config, MagicMock(), MagicMock(), OdpmCliArgs()
            )
            step = evaluate_secrets_materialize(ctx)
            self.assertEqual(step.outcome, "skip")


class CiSecretsOdpmCliSmokeTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.project_dir = provision_minimal_odpm_project(
            Path(self._tmp.name) / "project"
        )
        self._home = Path(self._tmp.name) / "home"
        self._home.mkdir()
        self._secrets_file = Path(self._tmp.name) / "incoming-secrets.json"
        self._secrets_file.write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "secrets": {"payment.api_key": "sk_ci_test"},
                }
            ),
            encoding="utf-8",
        )
        os.chmod(self._secrets_file, 0o600)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def _odpm_env(self) -> dict[str, str]:
        env = os.environ.copy()
        env["HOME"] = str(self._home)
        env["PWD"] = str(self.project_dir)
        return env

    def test_secrets_file_skip_start_materializes_and_compose_mount(self):
        odpm_py = Path(os.environ.get("ODPM_ODPM_PY", repo_root() / "odpm.py"))
        result = subprocess.run(
            [
                sys.executable,
                str(odpm_py),
                "--secrets-file",
                str(self._secrets_file),
                "--skip-start",
                "--no-git-update",
            ],
            cwd=self.project_dir,
            env=self._odpm_env(),
            capture_output=True,
            text=True,
            timeout=120,
        )
        self.assertEqual(
            result.returncode,
            0,
            msg=(result.stdout or "") + (result.stderr or ""),
        )

        source_path = self.project_dir / constants.ODPM_SECRETS_SOURCE_REL_PATH
        runtime_path = self.project_dir / constants.ODPM_SECRETS_RUNTIME_REL_PATH
        self.assertTrue(source_path.is_file())
        self.assertTrue(runtime_path.is_file())

        compose_text = (self.project_dir / "docker-compose.yml").read_text(
            encoding="utf-8"
        )
        self.assertIn(
            f"{constants.ODPM_SECRETS_PATH_ENV}={constants.ODPM_SECRETS_CONTAINER_PATH}",
            compose_text,
        )
        self.assertIn(
            f"{runtime_path}:{constants.ODPM_SECRETS_CONTAINER_PATH}:ro,Z",
            compose_text,
        )


if __name__ == "__main__":
    unittest.main()
