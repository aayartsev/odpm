"""CI bake must materialize ``odoo_config_data.options`` without template.odoo_conf."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.config.config import Config
from dev_project.config.odoo_conf import OdooConfBuilder
from dev_project.config.payload import write_runtime_config_to_path
from dev_project.config.state import BootstrapState, DockerLayoutState
from dev_project.config.transforms.env_substitution import EnvResolver
from dev_project.errors import ConfigError
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.manifest.reader import load_manifest
from dev_project.prepare.sources_only import IMAGE_ENSURE_STEP_IDS
from dev_project.project_env import CreateProjectEnvironment
from dev_project.project_env.ci_image import CiImageBuilder
from dev_project.project_env.secrets import write_secrets_source
from dev_project.project_env.services import CiImageBuildService
from dev_project.scenario_policy import ScenarioPolicy
from tests.test_manifest_v2_reader import _minimal_v2


class ImageEnsureStepIdsTests(unittest.TestCase):
    def test_image_ensure_excludes_template_odoo_conf(self):
        self.assertNotIn("template.odoo_conf", IMAGE_ENSURE_STEP_IDS)


class EnsureOdooConfigDataForBakeTests(unittest.TestCase):
    def test_ensure_fills_options_with_expanded_db_secrets(self):
        with tempfile.TemporaryDirectory() as project_dir:
            conf_path = Path(project_dir) / constants.ODOO_CONF_NAME
            conf_path.write_text(
                "[options]\ndb_host = db-dev\ndb_user = odoo\n",
                encoding="utf-8",
            )
            write_secrets_source(
                project_dir,
                {"pg_user": "ci_user", "pg_user_password": "s3cret"},
            )
            raw = _minimal_v2(
                requires_odpm="4.6.0",
                scenarios={
                    "ci": {
                        "odoo_conf": {
                            "options": {
                                "db_host": "10.241.2.102",
                                "db_port": 5000,
                                "db_user": "${@secret:pg_user}",
                                "db_password": "${@secret:pg_user_password}",
                            }
                        }
                    }
                },
            )
            # Bootstrap view without secrets — ensure must reload after disk secrets.
            view = load_manifest(
                raw,
                active_scenario=constants.CI_SCENARIO,
                env_resolver=None,
            )
            self.assertEqual(
                view.odoo_conf["options"]["db_user"],
                "${@secret:pg_user}",
            )

            config = Config.__new__(Config)
            config.project_dir = project_dir
            config._env_resolver = EnvResolver.from_sources(
                process_environ={},
                project_dotenv={},
                secrets={},
            )
            config.user_env = MagicMock(odpm_scenario=constants.CI_SCENARIO)
            config._bootstrap = BootstrapState(manifest_view=view)
            config._docker = DockerLayoutState(
                path_odoo_conf=str(conf_path),
                docker_dirs_with_addons=["/home/odoo/extra-addons"],
                docker_project_dir="/home/odoo",
            )
            config._odoo_conf = OdooConfBuilder(config)

            env = MagicMock(spec=CreateProjectEnvironment)
            env.config = config
            CiImageBuilder(env)._ensure_odoo_config_data_for_bake()

            options = config.docker_layout.odoo_config_data["options"]
            self.assertEqual(options["db_host"], "10.241.2.102")
            self.assertEqual(options["db_port"], "5000")
            self.assertEqual(options["db_user"], "ci_user")
            self.assertEqual(options["db_password"], "s3cret")
            self.assertIn("addons_path", options)

            # Same options must survive runtime JSON serialization used by CI bake.
            runtime_cfg = MagicMock()
            runtime_cfg.odoo_config_data = config.docker_layout.odoo_config_data
            runtime_cfg.docker_odoo_dir = "/home/odoo/odoo"
            runtime_cfg.docker_path_odoo_conf = "/home/odoo/odoo.conf"
            runtime_cfg.arguments = OdpmCliArgs()
            runtime_cfg.db_creation_data = dict(constants.DEFAULT_DB_CREATION_DATA)
            runtime_cfg.db_manager_password = ""
            runtime_cfg.docker_venv_dir = "/home/odoo/.venv"
            runtime_cfg.docker_project_dir = "/home/odoo"
            runtime_cfg.requirements_txt = []
            runtime_cfg.odoo_version = "19.0"
            runtime_cfg.python_version = "3.12"
            runtime_cfg.platform_name = "odoo"
            runtime_cfg.arch = "amd64"
            runtime_cfg.sql_queries = []
            runtime_cfg.update_modules = ""
            runtime_cfg.docker_dirs_with_addons = ["/home/odoo/extra-addons"]
            runtime_cfg.container_run_mode = constants.RUN_MODE_ODOO
            runtime_cfg.user_env = MagicMock(odpm_scenario=constants.CI_SCENARIO)
            runtime_cfg.policy = ScenarioPolicy.from_scenario(constants.CI_SCENARIO)
            runtime_cfg.compute_venv_lock_hash = MagicMock(return_value="lock")
            runtime_path = Path(project_dir) / "runtime" / "config.json"
            write_runtime_config_to_path(runtime_cfg, str(runtime_path))
            payload = json.loads(runtime_path.read_bytes())
            baked = payload["odoo_config_data"]["options"]
            self.assertEqual(baked["db_user"], "ci_user")
            self.assertEqual(baked["db_password"], "s3cret")
            self.assertEqual(baked["db_host"], "10.241.2.102")

    def test_ensure_missing_secret_raises(self):
        with tempfile.TemporaryDirectory() as project_dir:
            conf_path = Path(project_dir) / constants.ODOO_CONF_NAME
            conf_path.write_text("[options]\n", encoding="utf-8")
            raw = _minimal_v2(
                requires_odpm="4.6.0",
                scenarios={
                    "ci": {
                        "odoo_conf": {
                            "options": {
                                "db_password": "${@secret:missing_key}",
                            }
                        }
                    }
                },
            )
            view = load_manifest(
                raw,
                active_scenario=constants.CI_SCENARIO,
                env_resolver=None,
            )
            config = Config.__new__(Config)
            config.project_dir = project_dir
            config._env_resolver = EnvResolver.from_sources(
                process_environ={},
                project_dotenv={},
                secrets={},
            )
            config.user_env = MagicMock(odpm_scenario=constants.CI_SCENARIO)
            config._bootstrap = BootstrapState(manifest_view=view)
            config._docker = DockerLayoutState(
                path_odoo_conf=str(conf_path),
                docker_dirs_with_addons=[],
                docker_project_dir="/home/odoo",
            )
            config._odoo_conf = OdooConfBuilder(config)
            env = MagicMock(spec=CreateProjectEnvironment)
            env.config = config
            with self.assertRaises(ConfigError):
                CiImageBuilder(env)._ensure_odoo_config_data_for_bake()

    def test_prepare_ci_build_context_invokes_ensure_first(self):
        config = MagicMock()
        config.project_dir = "/tmp"
        config.ci_build_context_dir = "/tmp/ci-ctx"
        env = CreateProjectEnvironment(config)
        calls: list[str] = []

        def _tracking(self) -> None:
            calls.append("ensure")
            raise RuntimeError("stop-after-ensure")

        with patch.object(
            CiImageBuilder,
            "_ensure_odoo_config_data_for_bake",
            _tracking,
        ):
            with self.assertRaisesRegex(RuntimeError, "stop-after-ensure"):
                CiImageBuildService(env).prepare_ci_build_context()
        self.assertEqual(calls, ["ensure"])


if __name__ == "__main__":
    unittest.main()
