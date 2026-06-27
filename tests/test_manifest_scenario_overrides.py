"""Tests for per-scenario manifest overlays (4.7 PR1)."""

from __future__ import annotations

import unittest

from dev_project import constants
from dev_project.errors import ConfigError
from dev_project.manifest.compose_policy import RESERVED_MANIFEST_SERVICE_NAMES
from dev_project.manifest.schema import validate_manifest_v2
from dev_project.manifest.scenario_overrides import (
    ScenarioManifestSlice,
    manifest_uses_scenarios,
    merge_manifest_slice,
    resolve_effective_manifest_slice,
    top_level_slice,
    validate_scenario_manifest,
)
from tests.test_manifest_v2_reader import _minimal_v2


def _mailpit_service() -> dict:
    return {
        "mailpit": {
            "image": "axllent/mailpit:latest",
            "ports": ["8025:8025"],
            "depends_on": ["db"],
        }
    }


class ScenarioOverridesMergeTests(unittest.TestCase):
    def test_legacy_resolve_returns_top_level_only(self):
        raw = _minimal_v2(
            odoo_conf={"options": {"workers": "0"}},
            requirements=["requests==2.31.0"],
        )
        self.assertFalse(manifest_uses_scenarios(raw))
        effective = resolve_effective_manifest_slice(raw, constants.SERVER_SCENARIO)
        self.assertEqual(effective.odoo_conf, {"options": {"workers": "0"}})
        self.assertEqual(effective.requirements, ["requests==2.31.0"])

    def test_multi_mode_with_empty_scenarios_object(self):
        raw = _minimal_v2(
            scenarios={},
            odoo_conf={"options": {"proxy_mode": "True"}},
        )
        self.assertTrue(manifest_uses_scenarios(raw))
        effective = resolve_effective_manifest_slice(raw, constants.CI_SCENARIO)
        self.assertEqual(effective.odoo_conf, {"options": {"proxy_mode": "True"}})

    def test_multi_partial_overlay_merges_odoo_conf_and_requirements(self):
        raw = _minimal_v2(
            scenarios={
                "server": {
                    "odoo_conf": {"options": {"workers": "4"}},
                    "requirements": ["gunicorn"],
                }
            },
            odoo_conf={"options": {"workers": "0", "proxy_mode": "True"}},
            requirements=["requests==2.31.0"],
        )
        dev = resolve_effective_manifest_slice(raw, constants.DEVELOPER_SCENARIO)
        server = resolve_effective_manifest_slice(raw, constants.SERVER_SCENARIO)
        self.assertEqual(
            dev.odoo_conf,
            {"options": {"workers": "0", "proxy_mode": "True"}},
        )
        self.assertEqual(dev.requirements, ["requests==2.31.0"])
        self.assertEqual(
            server.odoo_conf,
            {"options": {"workers": "4", "proxy_mode": "True"}},
        )
        self.assertEqual(
            server.requirements,
            ["requests==2.31.0", "gunicorn"],
        )

    def test_requirements_dedupe_preserves_first_occurrence(self):
        base = ScenarioManifestSlice(requirements=["pkg-a", "pkg-b"])
        overlay = ScenarioManifestSlice(requirements=["pkg-b", "pkg-c"])
        merged = merge_manifest_slice(base, overlay)
        self.assertEqual(merged.requirements, ["pkg-a", "pkg-b", "pkg-c"])

    def test_service_patches_merge_uses_adr009_rules(self):
        base = ScenarioManifestSlice(
            service_patches={
                "odoo": {
                    "environment": {"BASE": "1"},
                    "ports": ["8069:8069"],
                }
            }
        )
        overlay = ScenarioManifestSlice(
            service_patches={
                "odoo": {
                    "environment": {"EXTRA": "2"},
                }
            }
        )
        merged = merge_manifest_slice(base, overlay)
        self.assertIsNotNone(merged.service_patches)
        odoo_patch = merged.service_patches["odoo"]
        self.assertEqual(odoo_patch["ports"], ["8069:8069"])
        env = odoo_patch["environment"]
        if isinstance(env, dict):
            self.assertEqual(env, {"BASE": "1", "EXTRA": "2"})
        else:
            self.assertEqual(sorted(env), ["BASE=1", "EXTRA=2"])

    def test_services_overlay_replaces_sidecar_by_name(self):
        raw = _minimal_v2(
            scenarios={
                "developer": {
                    "services": {
                        "mailpit": {
                            "image": "axllent/mailpit:dev",
                            "ports": ["8025:8025"],
                        }
                    }
                }
            },
            services=_mailpit_service(),
        )
        effective = resolve_effective_manifest_slice(raw, constants.DEVELOPER_SCENARIO)
        self.assertEqual(
            effective.services["mailpit"]["image"],
            "axllent/mailpit:dev",
        )

    def test_unknown_active_scenario_falls_back_to_developer_overlay(self):
        raw = _minimal_v2(
            scenarios={
                "developer": {"requirements": ["dev-only"]},
            }
        )
        effective = resolve_effective_manifest_slice(raw, "staging")
        self.assertEqual(effective.requirements, ["dev-only"])


class ScenarioOverridesSchemaTests(unittest.TestCase):
    def test_schema_accepts_valid_scenarios(self):
        validate_manifest_v2(
            _minimal_v2(
                requires_odpm="4.6.0",
                scenarios={
                    "developer": {"requirements": ["debugpy"]},
                    "server": {
                        "odoo_conf": {"options": {"workers": "4"}},
                    },
                },
            )
        )

    def test_schema_rejects_unknown_scenario_key(self):
        with self.assertRaises(ConfigError):
            validate_manifest_v2(
                _minimal_v2(
                    requires_odpm="4.6.0",
                    scenarios={"staging": {"requirements": ["x"]}},
                )
            )


class ScenarioOverridesValidateTests(unittest.TestCase):
    def test_validate_accepts_legacy_v2_without_scenarios(self):
        validate_scenario_manifest(
            _minimal_v2(
                odoo_conf={"options": {"proxy_mode": "True"}},
                services=_mailpit_service(),
            )
        )

    def test_validate_multi_effective_slices(self):
        validate_scenario_manifest(
            _minimal_v2(
                requires_odpm="4.6.0",
                scenarios={
                    "developer": {"requirements": ["ipython"]},
                    "server": {"odoo_conf": {"options": {"workers": "2"}}},
                },
                services=_mailpit_service(),
            )
        )

    def test_validate_rejects_v1_with_scenarios(self):
        with self.assertRaises(ConfigError) as ctx:
            validate_scenario_manifest(
                {
                    "odpm_version": "4.0",
                    "odoo_version": "17.0",
                    "scenarios": {"developer": {}},
                }
            )
        self.assertIn("manifest migrate", str(ctx.exception).lower())

    def test_validate_rejects_reserved_odoo_conf_in_effective_slice(self):
        with self.assertRaises(ConfigError) as ctx:
            validate_scenario_manifest(
                _minimal_v2(
                    requires_odpm="4.6.0",
                    scenarios={
                        "server": {
                            "odoo_conf": {
                                "options": {"db_host": "wrong"},
                            }
                        }
                    },
                )
            )
        self.assertIn("db_host", str(ctx.exception))

    def test_validate_rejects_reserved_service_name_in_scenario_overlay(self):
        with self.assertRaises(ConfigError) as ctx:
            validate_scenario_manifest(
                _minimal_v2(
                    requires_odpm="4.6.0",
                    scenarios={
                        "developer": {
                            "services": {
                                "odoo": {"image": "evil"},
                            }
                        }
                    },
                )
            )
        self.assertIn("odoo", str(ctx.exception))
        self.assertIn("service_patches", str(ctx.exception).lower())

    def test_top_level_slice_extracts_fields(self):
        raw = _minimal_v2(
            requirements=["a"],
            services=_mailpit_service(),
            service_patches={"odoo": {"user": "9999"}},
        )
        slice_ = top_level_slice(raw)
        self.assertEqual(slice_.requirements, ["a"])
        self.assertIn("mailpit", slice_.services or {})
        self.assertIn("odoo", slice_.service_patches or {})

    def test_reserved_names_documented(self):
        self.assertIn("odoo", RESERVED_MANIFEST_SERVICE_NAMES)
        self.assertIn("db", RESERVED_MANIFEST_SERVICE_NAMES)

    def test_warns_when_sidecar_references_stack_without_env(self):
        with self.assertLogs("dev_project.manifest.compose_policy", level="WARNING") as logs:
            validate_scenario_manifest(
                _minimal_v2(
                    services={
                        "mailpit": {
                            "image": "axllent/mailpit",
                            "networks": ["stack"],
                        }
                    },
                ),
                compose_network_logical=None,
            )
        self.assertTrue(any("networks references logical network" in msg for msg in logs.output))

    def test_no_warn_when_env_matches_stack(self):
        with self.assertNoLogs("dev_project.manifest.compose_policy", level="WARNING"):
            validate_scenario_manifest(
                _minimal_v2(
                    services={
                        "mailpit": {
                            "image": "axllent/mailpit",
                            "networks": ["stack"],
                        }
                    },
                ),
                compose_network_logical="stack",
            )

    def test_warns_when_env_proxy_but_manifest_stack(self):
        services = _mailpit_service()
        services["mailpit"] = {**services["mailpit"], "networks": ["stack"]}
        with self.assertLogs("dev_project.manifest.compose_policy", level="WARNING"):
            validate_scenario_manifest(
                _minimal_v2(services=services),
                compose_network_logical="proxy",
            )


class ScenarioOverridesLoadWireTests(unittest.TestCase):
    def test_manifest_view_exposes_scenario_slice_after_load(self):
        from dev_project.manifest.reader import load_manifest

        view = load_manifest(
            _minimal_v2(
                requires_odpm="4.6.0",
                scenarios={"developer": {"requirements": ["ipython"]}},
            ),
            active_scenario=constants.DEVELOPER_SCENARIO,
        )
        self.assertIsNotNone(view.scenario_slice)
        self.assertEqual(view.scenario_slice.requirements, ["ipython"])


if __name__ == "__main__":
    unittest.main()
