"""Integration tests for CI manifest db_* override (ADR-022)."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.config.odoo_conf import OdooConfBuilder
from dev_project.config.state import AddonLayoutState, BootstrapState, DockerLayoutState
from dev_project.config.transforms.env_substitution import EnvResolver
from dev_project.database.drift import (
    detect_database_drift,
    detect_database_drift_for_config,
)
from dev_project.database.schema import (
    DatabaseClusterFingerprint,
    DatabaseComposeFingerprint,
    DatabaseCurrentState,
    DatabaseOdooConfFingerprint,
)
from dev_project.manifest.odoo_conf_policy import ci_manifest_db_override
from dev_project.manifest.reader import ManifestView, load_manifest
from dev_project.prepare.steps_template import evaluate_template_odoo_conf
from dev_project.scenario_policy import ScenarioPolicy
from tests.test_manifest_v2_reader import _minimal_v2
from tests.test_plan_database_drift import PlanDatabaseDriftTests


class CiManifestDbOverrideHelperTests(unittest.TestCase):
    def test_ci_manifest_db_override_requires_ci_and_db_keys(self):
        view = ManifestView(
            manifest_schema=2,
            requires_odpm="4.6.0",
            raw_normalized={},
            odoo_conf={"options": {"db_host": "10.0.0.1"}},
        )
        self.assertTrue(ci_manifest_db_override(view, is_ci=True))
        self.assertFalse(ci_manifest_db_override(view, is_ci=False))
        self.assertFalse(ci_manifest_db_override(None, is_ci=True))
        self.assertFalse(
            ci_manifest_db_override(
                ManifestView(
                    manifest_schema=2,
                    requires_odpm="4.6.0",
                    raw_normalized={},
                    odoo_conf={"options": {"proxy_mode": "True"}},
                ),
                is_ci=True,
            )
        )


class CiManifestDbOverrideMergeTests(unittest.TestCase):
    def test_generate_odoo_conf_docker_data_merges_ci_db_keys(self):
        with tempfile.TemporaryDirectory() as project_dir:
            conf_path = Path(project_dir) / constants.ODOO_CONF_NAME
            conf_path.write_text(
                "\n".join(
                    [
                        "[options]",
                        "db_host = db-dev",
                        "db_port = 5432",
                        "db_user = odoo",
                        "db_password = odoo",
                        "proxy_mode = False",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            config = MagicMock()
            config.docker_layout = DockerLayoutState(
                path_odoo_conf=str(conf_path),
                docker_dirs_with_addons=["/home/odoo/extra-addons"],
                docker_project_dir="/home/odoo",
            )
            config.addon_layout = AddonLayoutState()
            config.path_odoo_conf = str(conf_path)
            config.bootstrap = BootstrapState(
                manifest_view=ManifestView(
                    manifest_schema=2,
                    requires_odpm="4.6.0",
                    raw_normalized={},
                    odoo_conf={
                        "options": {
                            "db_host": "10.241.2.102",
                            "db_port": "5000",
                            "db_user": "ci_user",
                            "db_password": "ci_pass",
                            "proxy_mode": "True",
                        }
                    },
                )
            )

            OdooConfBuilder(config).generate_odoo_conf_docker_data()
            options = config.docker_layout.odoo_config_data["options"]
            self.assertEqual(options["db_host"], "10.241.2.102")
            self.assertEqual(options["db_port"], "5000")
            self.assertEqual(options["db_user"], "ci_user")
            self.assertEqual(options["db_password"], "ci_pass")
            self.assertEqual(options["proxy_mode"], "True")
            self.assertEqual(options["addons_path"], "/home/odoo/extra-addons")


class CiManifestDbOverrideTemplateTests(PlanDatabaseDriftTests):
    def test_template_odoo_conf_skips_db_host_mismatch_when_ci_override(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = self._config(project_dir)
            config.policy = ScenarioPolicy.from_scenario(constants.CI_SCENARIO)
            config.bootstrap = BootstrapState(
                manifest_view=ManifestView(
                    manifest_schema=2,
                    requires_odpm="4.6.0",
                    raw_normalized={},
                    odoo_conf={
                        "options": {
                            "db_host": "10.241.2.102",
                            "db_port": "5000",
                            "db_user": "ci",
                            "db_password": "secret",
                        }
                    },
                )
            )
            self._write_odoo_conf_template(project_dir)
            self._write_odoo_conf(project_dir, db_host="10.241.2.102")
            step = evaluate_template_odoo_conf(self._ctx(config))
            self.assertEqual(step.id, "template.odoo_conf")
            self.assertEqual(step.outcome, "noop")

    def test_template_odoo_conf_still_updates_mismatch_without_ci_override(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = self._config(project_dir)
            config.policy = ScenarioPolicy.from_scenario(constants.CI_SCENARIO)
            config.bootstrap = BootstrapState(
                manifest_view=ManifestView(
                    manifest_schema=2,
                    requires_odpm="4.6.0",
                    raw_normalized={},
                    odoo_conf={"options": {"proxy_mode": "True"}},
                )
            )
            self._write_odoo_conf_template(project_dir)
            self._write_odoo_conf(project_dir, db_host="db")
            step = evaluate_template_odoo_conf(self._ctx(config))
            self.assertEqual(step.outcome, "update")
            self.assertIn("db-dev", step.reason)


class CiManifestDbOverrideDriftTests(unittest.TestCase):
    def test_detect_skips_db_host_mismatch_flag(self):
        current = DatabaseCurrentState(
            odpm_scenario=constants.CI_SCENARIO,
            engine="postgres",
            compose=DatabaseComposeFingerprint(
                service_name="db-dev",
                compose_project_name="proj",
                host_port=5432,
                data_path_abs="/tmp/pg",
                image_tag="postgres:17",
            ),
            odoo_conf=DatabaseOdooConfFingerprint(
                db_host="10.241.2.102",
                db_port=5000,
                db_user="ci",
            ),
            cluster=DatabaseClusterFingerprint(
                data_dir_nonempty=True,
                pg_major=17,
                app_role="odoo",
                app_role_present=True,
            ),
        )
        kinds = {d.kind for d in detect_database_drift(current, None)}
        self.assertIn("db_host_mismatch", kinds)
        kinds_skip = {
            d.kind
            for d in detect_database_drift(
                current, None, skip_db_host_mismatch=True
            )
        }
        self.assertNotIn("db_host_mismatch", kinds_skip)

    def test_detect_for_config_skips_when_ci_override(self):
        with tempfile.TemporaryDirectory() as project_dir:
            Path(project_dir, constants.ODOO_CONF_NAME).write_text(
                "\n".join(
                    [
                        "[options]",
                        "db_host = 10.241.2.102",
                        "db_port = 5000",
                        "db_user = ci",
                        "db_password = secret",
                    ]
                )
                + "\n",
                encoding="utf-8",
            )
            data_path = os.path.join(
                project_dir, constants.POSTGRES_LOCAL_STORAGE_DIR
            )
            os.makedirs(data_path, exist_ok=True)
            (Path(data_path) / "PG_VERSION").write_text("17\n", encoding="utf-8")

            config = MagicMock()
            config.project_dir = project_dir
            config.policy = ScenarioPolicy.from_scenario(constants.CI_SCENARIO)
            config.postgres_version = "17"
            config.postgres_data_local_storage = data_path
            config.user_env.postgres_service_name = "db-dev"
            config.user_env.postgres_port = 5432
            config.addon_layout = AddonLayoutState()
            config.docker_layout = DockerLayoutState(
                path_odoo_conf=os.path.join(project_dir, constants.ODOO_CONF_NAME),
            )
            config.path_odoo_conf = config.docker_layout.path_odoo_conf
            config.bootstrap = BootstrapState(
                manifest_view=ManifestView(
                    manifest_schema=2,
                    requires_odpm="4.6.0",
                    raw_normalized={},
                    odoo_conf={
                        "options": {
                            "db_host": "10.241.2.102",
                            "db_port": "5000",
                            "db_user": "ci",
                            "db_password": "secret",
                        }
                    },
                )
            )
            _current, drifts = detect_database_drift_for_config(config)
            kinds = {d.kind for d in drifts}
            self.assertNotIn("db_host_mismatch", kinds)


class CiManifestDbOverrideSecretTests(unittest.TestCase):
    def test_load_manifest_expands_secret_in_ci_db_password(self):
        resolver = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={},
            secrets={
                "pg_user": "ci_user",
                "pg_user_password": "s3cret",
            },
        )
        view = load_manifest(
            _minimal_v2(
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
            ),
            active_scenario=constants.CI_SCENARIO,
            env_resolver=resolver,
        )
        options = view.odoo_conf["options"]
        self.assertEqual(options["db_host"], "10.241.2.102")
        self.assertEqual(options["db_user"], "ci_user")
        self.assertEqual(options["db_password"], "s3cret")


if __name__ == "__main__":
    unittest.main()
