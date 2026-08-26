"""Tests for manifest secrets requirements (4.7)."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.manifest.schema import validate_manifest_v2
from dev_project.manifest.scenario_overrides import (
    resolve_effective_manifest_slice,
    slice_from_manifest_fields,
)
from dev_project.manifest.secrets_policy import (
    ManifestSecretsSpec,
    collect_secrets_requirement_issues,
    merge_secrets_spec,
    read_secrets_example_keys,
)
from dev_project.prepare.execute import collect_prepare_warnings
from dev_project.project_env.secrets import write_secrets_source
from dev_project.runtime_coordinator import RuntimeCoordinator
from dev_project.scenario_policy import ScenarioPolicy
from tests.test_manifest_v2_reader import _minimal_v2


class ManifestSecretsSchemaTests(unittest.TestCase):
    def test_schema_accepts_root_and_overlay_secrets(self):
        raw = _minimal_v2(
            secrets={"required": True, "keys": ["payment.api_key"]},
            scenarios={
                "developer": {
                    "secrets": {"keys": ["armtek.token"]},
                },
                "ci": {
                    "secrets": {"required": False},
                },
            },
        )
        validate_manifest_v2(raw)

    def test_schema_accepts_secrets_provider(self):
        raw = _minimal_v2(
            secrets={
                "required": True,
                "keys": ["payment_provider.api_key"],
                "provider": {
                    "type": "infisical",
                    "host": "https://app.infisical.com",
                    "project_id": "proj",
                    "environment_slug": "dev",
                    "secret_path": "/odoo",
                    "recursive": False,
                    "key_map": {"PAYMENT_API_KEY": "payment_provider.api_key"},
                },
            },
        )
        validate_manifest_v2(raw)


class ManifestSecretsMergeTests(unittest.TestCase):
    def test_merge_keys_dedupes_and_overlay_required_overrides(self):
        merged = merge_secrets_spec(
            {"required": True, "keys": ["a", "b"]},
            {"required": False},
        )
        self.assertIsNotNone(merged)
        assert merged is not None
        self.assertFalse(merged.required)
        self.assertEqual(merged.keys, ("a", "b"))

    def test_resolve_effective_slice_merges_secrets(self):
        raw = _minimal_v2(
            secrets={"required": True, "keys": ["shared.key"]},
            scenarios={
                "developer": {"secrets": {"keys": ["dev.only"]}},
            },
        )
        dev = resolve_effective_manifest_slice(raw, constants.DEVELOPER_SCENARIO)
        self.assertTrue(dev.secrets is not None and dev.secrets.required)
        self.assertEqual(
            dev.secrets.keys,
            ("shared.key", "dev.only"),
        )
        ci = resolve_effective_manifest_slice(raw, constants.CI_SCENARIO)
        self.assertIsNotNone(ci.secrets)
        assert ci.secrets is not None
        self.assertTrue(ci.secrets.required)

    def test_ci_overlay_can_disable_required(self):
        raw = _minimal_v2(
            secrets={"required": True, "keys": ["api.key"]},
            scenarios={"ci": {"secrets": {"required": False}}},
        )
        ci = resolve_effective_manifest_slice(raw, constants.CI_SCENARIO)
        self.assertIsNotNone(ci.secrets)
        assert ci.secrets is not None
        self.assertFalse(ci.secrets.required)
        self.assertEqual(ci.secrets.keys, ("api.key",))

    def test_overlay_replaces_provider_object(self):
        merged = merge_secrets_spec(
            {
                "required": True,
                "keys": ["shared"],
                "provider": {"type": "file", "host": "https://keep.example"},
            },
            {
                "keys": ["dev.only"],
                "provider": {
                    "type": "infisical",
                    "project_id": "proj",
                    "environment_slug": "dev",
                },
            },
        )
        self.assertIsNotNone(merged)
        assert merged is not None
        self.assertEqual(merged.keys, ("shared", "dev.only"))
        self.assertIsNotNone(merged.provider)
        assert merged.provider is not None
        self.assertEqual(merged.provider.type, "infisical")
        self.assertEqual(merged.provider.project_id, "proj")
        self.assertIsNone(merged.provider.host)

    def test_overlay_without_provider_keeps_base(self):
        merged = merge_secrets_spec(
            {"provider": {"type": "infisical", "host": "https://a.example"}},
            {"keys": ["x"]},
        )
        self.assertIsNotNone(merged)
        assert merged is not None
        self.assertEqual(merged.keys, ("x",))
        self.assertEqual(merged.provider.type, "infisical")
        self.assertEqual(merged.provider.host, "https://a.example")

    def test_resolve_effective_slice_replaces_provider(self):
        raw = _minimal_v2(
            secrets={"provider": {"type": "file"}},
            scenarios={
                "ci": {
                    "secrets": {
                        "provider": {
                            "type": "infisical",
                            "project_slug": "acme",
                            "environment_slug": "ci",
                        }
                    }
                }
            },
        )
        ci = resolve_effective_manifest_slice(raw, constants.CI_SCENARIO)
        self.assertIsNotNone(ci.secrets)
        assert ci.secrets is not None and ci.secrets.provider is not None
        self.assertEqual(ci.secrets.provider.type, "infisical")
        self.assertEqual(ci.secrets.provider.project_slug, "acme")
        dev = resolve_effective_manifest_slice(raw, constants.DEVELOPER_SCENARIO)
        self.assertEqual(dev.secrets.provider.type, "file")


class ManifestSecretsRequirementTests(unittest.TestCase):
    def _write_example(self, project_dir: str, keys: dict[str, str]) -> None:
        path = Path(project_dir) / constants.ODPM_SECRETS_EXAMPLE_REL_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"schema_version": 1, "secrets": keys}),
            encoding="utf-8",
        )

    def test_required_without_keys_only_checks_file_presence(self):
        with tempfile.TemporaryDirectory() as project_dir:
            self._write_example(project_dir, {"payment.api.key": "REPLACE_ME"})
            write_secrets_source(project_dir, {"payment.api.key": "REPLACE_ME"})
            spec = ManifestSecretsSpec(required=True)
            issues = collect_secrets_requirement_issues(
                project_dir,
                spec,
                mount_secrets_from_host=True,
                scenario=constants.DEVELOPER_SCENARIO,
            )
            self.assertEqual(issues, [])

    def test_missing_source_mentions_scenario_and_example_keys_as_hint(self):
        with tempfile.TemporaryDirectory() as project_dir:
            self._write_example(project_dir, {"payment.api_key": "REPLACE_ME"})
            spec = ManifestSecretsSpec(required=True)
            issues = collect_secrets_requirement_issues(
                project_dir,
                spec,
                mount_secrets_from_host=True,
                scenario=constants.DEVELOPER_SCENARIO,
            )
            self.assertEqual(len(issues), 1)
            self.assertIn(constants.DEVELOPER_SCENARIO, issues[0])
            self.assertIn("payment.api_key", issues[0])
            self.assertIn("secrets.example.json", issues[0])

    def test_missing_source_without_example_omits_key_list(self):
        with tempfile.TemporaryDirectory() as project_dir:
            spec = ManifestSecretsSpec(required=True)
            issues = collect_secrets_requirement_issues(
                project_dir,
                spec,
                mount_secrets_from_host=True,
                scenario=constants.SERVER_SCENARIO,
            )
            self.assertEqual(len(issues), 1)
            self.assertIn(constants.SERVER_SCENARIO, issues[0])
            self.assertNotIn("with keys:", issues[0])

    def test_placeholder_values_report_issue_only_with_manifest_keys(self):
        with tempfile.TemporaryDirectory() as project_dir:
            write_secrets_source(project_dir, {"payment.api_key": "REPLACE_ME"})
            spec = ManifestSecretsSpec(required=True, keys=("payment.api_key",))
            issues = collect_secrets_requirement_issues(
                project_dir,
                spec,
                mount_secrets_from_host=True,
                scenario=constants.DEVELOPER_SCENARIO,
            )
            self.assertEqual(len(issues), 1)
            self.assertIn("payment.api_key", issues[0])

    def test_explicit_keys_missing_from_source(self):
        with tempfile.TemporaryDirectory() as project_dir:
            write_secrets_source(project_dir, {"other": "value"})
            spec = ManifestSecretsSpec(required=True, keys=("payment.api_key",))
            issues = collect_secrets_requirement_issues(
                project_dir,
                spec,
                mount_secrets_from_host=True,
                scenario=constants.DEVELOPER_SCENARIO,
            )
            self.assertEqual(len(issues), 1)
            self.assertIn("payment.api_key", issues[0])

    def test_satisfied_explicit_keys_produce_no_issues(self):
        with tempfile.TemporaryDirectory() as project_dir:
            write_secrets_source(project_dir, {"payment.api_key": "sk_live"})
            spec = ManifestSecretsSpec(required=True, keys=("payment.api_key",))
            issues = collect_secrets_requirement_issues(
                project_dir,
                spec,
                mount_secrets_from_host=True,
                scenario=constants.DEVELOPER_SCENARIO,
            )
            self.assertEqual(issues, [])

    def test_ci_mount_disabled_skips_checks(self):
        with tempfile.TemporaryDirectory() as project_dir:
            spec = ManifestSecretsSpec(required=True, keys=("a",))
            issues = collect_secrets_requirement_issues(
                project_dir,
                spec,
                mount_secrets_from_host=False,
                scenario=constants.CI_SCENARIO,
            )
            self.assertEqual(issues, [])

    def test_read_secrets_example_keys_is_hint_only(self):
        with tempfile.TemporaryDirectory() as project_dir:
            self._write_example(
                project_dir,
                {"one": "REPLACE_ME", "two": "REPLACE_ME"},
            )
            self.assertEqual(
                read_secrets_example_keys(project_dir),
                ("one", "two"),
            )


class ManifestSecretsPlanIntegrationTests(unittest.TestCase):
    def test_prepare_warnings_include_missing_secrets(self):
        with tempfile.TemporaryDirectory() as project_dir:
            odpm_dir = Path(project_dir) / constants.PROJECT_SERVICE_DIRECTORY
            odpm_dir.mkdir(parents=True)
            example = odpm_dir / "secrets.example.json"
            example.write_text(
                json.dumps(
                    {
                        "schema_version": 1,
                        "secrets": {"api.key": "REPLACE_ME"},
                    }
                ),
                encoding="utf-8",
            )
            manifest_view = MagicMock()
            manifest_view.manifest_schema = constants.MANIFEST_SCHEMA_V2
            manifest_view.scenario_slice = slice_from_manifest_fields(
                secrets={"required": True},
            )
            ctx = MagicMock()
            ctx.host_ctx.project_dir = project_dir
            ctx.host_ctx.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
            ctx.host_ctx.update_lock = False
            ctx.host_ctx.skip_git_update = False
            ctx.host_ctx.sync_manifest_locks = False
            ctx.manifest_view = manifest_view
            warnings = collect_prepare_warnings(ctx)
            self.assertTrue(
                any(constants.DEVELOPER_SCENARIO in warning for warning in warnings)
            )
            self.assertTrue(any("secrets.json" in warning for warning in warnings))


class RuntimeCoordinatorSecretsGuardTests(unittest.TestCase):
    @patch(
        "dev_project.runtime_coordinator.should_force_recreate_compose_for_host",
        return_value=False,
    )
    @patch("dev_project.project_env.services.BaseImageService")
    @patch("dev_project.runtime_coordinator.run_logged", return_value=0)
    @patch("dev_project.extensions.hooks.run_lifecycle_hooks")
    @patch("dev_project.database.resolve.ensure_no_blocking_database_drift")
    @patch("dev_project.database.adopt.adopt_database_baseline")
    def test_run_after_prepare_fails_when_required_secrets_missing(
        self,
        _mock_adopt,
        _mock_drift,
        _mock_hooks,
        _mock_run,
        _mock_base_image,
        _mock_force,
    ):
        from dev_project.errors import PipelineError
        from dev_project.manifest.reader import ManifestView

        with tempfile.TemporaryDirectory() as project_dir:
            config = MagicMock()
            config.project_dir = project_dir
            config.program_dir = "/opt/odpm"
            config.config_home_dir = project_dir
            config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
            config.user_env = MagicMock()
            config.user_env.odoo_port = 8069
            config.user_settings = MagicMock()
            config.project_settings = MagicMock()
            config.docker_layout = MagicMock()
            config.addon_layout = MagicMock()
            config.no_log_prefix = False
            config.docker_compose_command = "docker compose"
            config.odoo_image_name = "odoo:dev"
            config.bootstrap.manifest_view = ManifestView(
                manifest_schema=constants.MANIFEST_SCHEMA_V2,
                requires_odpm="4.7.0",
                raw_normalized={},
                scenario_slice=slice_from_manifest_fields(
                    secrets={"required": True, "keys": ["api.key"]},
                ),
            )
            coordinator = RuntimeCoordinator(OdpmCliArgs(skip_start=False), config, MagicMock())
            coordinator.handle_build_image = MagicMock(return_value=False)
            coordinator.write_debug_profile = MagicMock()
            coordinator.configure_ide = MagicMock()
            with self.assertRaises(PipelineError) as ctx:
                coordinator.run_after_prepare()
            self.assertIn("api.key", str(ctx.exception))


if __name__ == "__main__":
    unittest.main()
