"""CI secrets import smoke (TD-FEAT-09): developer mount + ci image bake."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.prepare import make_prepare_context
from dev_project.prepare.steps_secrets import evaluate_secrets_materialize
from dev_project.project_env import CreateProjectEnvironment
from dev_project.project_env.secrets import (
    bake_secrets_enabled,
    import_secrets_from_path,
    materialize_secrets,
    prepare_secrets_for_ci_bake,
    secrets_runtime_path,
    secrets_source_path,
)
from dev_project.project_env.services import CiImageBuildService
from dev_project.scenario_policy import ScenarioPolicy
from tests.fixtures.minimal_odpm_fixture import provision_minimal_odpm_project
from tests.odpm_subprocess import run_odpm


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


class CiSecretsBakeTests(unittest.TestCase):
    def _program_dir(self) -> str:
        return str(Path(__file__).resolve().parents[1])

    def _make_ci_env(self, project_dir: str) -> CreateProjectEnvironment:
        config = MagicMock()
        config.program_dir = self._program_dir()
        config.project_dir = project_dir
        config.ci_build_context_dir = os.path.join(
            project_dir, constants.CI_BUILD_CONTEXT_DIR
        )
        config.odoo_config_data = {"options": {"admin_passwd": "admin"}}
        config.docker_project_dir = "/home/odoo"
        config.docker_venv_dir = "/home/odoo/.venv"
        config.docker_dev_project_dir = "/home/odoo/dev_project"
        config.docker_backups_dir = "/home/odoo/backups"
        config.docker_temp_tests_dir = "/tmp/odoo_tests"
        config.docker_odoo_dir = "/home/odoo/odoo"
        config.docker_extra_addons = "/home/odoo/extra-addons"
        config.docker_path_odoo_conf = "/home/odoo/odoo.conf"
        config.compute_venv_lock_hash.return_value = "abc"
        config.python_version = "3.12"
        config.requirements_txt = []
        config.arch = "amd64"
        config.odoo_version = "19.0"
        config.platform_name = "odoo"
        config.container_run_mode = constants.RUN_MODE_ODOO
        config.db_manager_password = ""
        config.db_creation_data = dict(constants.DEFAULT_DB_CREATION_DATA)
        config.arguments = OdpmCliArgs()
        config.sql_queries = []
        config.update_modules = ""
        config.docker_dirs_with_addons = []
        config.odoo_image_name = "odoo-base:test"
        config.user_env = MagicMock(odpm_scenario=constants.CI_SCENARIO)
        config.policy = ScenarioPolicy.from_scenario(constants.CI_SCENARIO)
        env = CreateProjectEnvironment(config)
        env.mapped_folders = []
        return env

    def test_bake_secrets_enabled_reads_env(self):
        with patch.dict(os.environ, {constants.ODPM_BAKE_SECRETS_ENV: "1"}):
            self.assertTrue(bake_secrets_enabled())
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop(constants.ODPM_BAKE_SECRETS_ENV, None)
            self.assertFalse(bake_secrets_enabled())

    def test_prepare_secrets_for_ci_bake_noop_without_flag(self):
        with tempfile.TemporaryDirectory() as project_dir:
            import_secrets_from_path(
                project_dir,
                self._write_external_secrets(project_dir),
            )
            self.assertFalse(prepare_secrets_for_ci_bake(project_dir))

    def test_prepare_ci_build_context_bakes_secrets_when_flag_set(self):
        with tempfile.TemporaryDirectory() as project_dir:
            import_secrets_from_path(
                project_dir,
                self._write_external_secrets(project_dir),
            )
            with patch.dict(
                os.environ, {constants.ODPM_BAKE_SECRETS_ENV: "1"}
            ):
                service = CiImageBuildService(self._make_ci_env(project_dir))
                service.prepare_ci_build_context()
                dockerfile = Path(service.generate_ci_dockerfile()).read_text(
                    encoding="utf-8"
                )

            baked_path = (
                Path(project_dir)
                / constants.CI_BUILD_CONTEXT_DIR
                / constants.CI_SECRETS_RUNTIME_CONTEXT_REL_PATH
            )
            self.assertTrue(baked_path.is_file())
            payload = json.loads(baked_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["secrets"]["payment.api_key"], "sk_ci_bake")

            self.assertIn(
                f"COPY --chown={constants.CONTAINER_USER}:{constants.CONTAINER_USER} "
                f"{constants.CI_SECRETS_RUNTIME_CONTEXT_REL_PATH} "
                f"{constants.ODPM_SECRETS_CONTAINER_PATH}",
                dockerfile,
            )
            self.assertIn(
                f"ENV {constants.ODPM_SECRETS_PATH_ENV}="
                f"{constants.ODPM_SECRETS_CONTAINER_PATH}",
                dockerfile,
            )

    def test_prepare_ci_build_context_skips_bake_without_secrets(self):
        with tempfile.TemporaryDirectory() as project_dir:
            with patch.dict(
                os.environ, {constants.ODPM_BAKE_SECRETS_ENV: "1"}
            ):
                service = CiImageBuildService(self._make_ci_env(project_dir))
                service.prepare_ci_build_context()
                dockerfile = Path(service.generate_ci_dockerfile()).read_text(
                    encoding="utf-8"
                )

            baked_path = (
                Path(project_dir)
                / constants.CI_BUILD_CONTEXT_DIR
                / constants.CI_SECRETS_RUNTIME_CONTEXT_REL_PATH
            )
            self.assertFalse(baked_path.exists())
            self.assertNotIn(constants.ODPM_SECRETS_CONTAINER_PATH, dockerfile)

    def _write_external_secrets(self, directory: str) -> str:
        path = os.path.join(directory, "incoming-secrets.json")
        Path(path).write_text(
            json.dumps(
                {
                    "schema_version": 1,
                    "secrets": {"payment.api_key": "sk_ci_bake"},
                }
            ),
            encoding="utf-8",
        )
        os.chmod(path, 0o600)
        return path


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

    def test_secrets_file_skip_start_materializes_and_compose_mount(self):
        result = run_odpm(
            "--secrets-file",
            str(self._secrets_file),
            "--skip-start",
            "--no-git-update",
            cwd=self.project_dir,
            env={"HOME": str(self._home)},
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
