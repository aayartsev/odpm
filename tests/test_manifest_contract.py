"""4.4 manifest and extension contract tests (no Docker required)."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.errors import ConfigError
from dev_project.compose.fragments import collect_compose_services, render_compose_services_block
from dev_project.extensions.context import ExtensionHostContext
from dev_project.extensions.reference.mailpit import (
    MAILPIT_SERVICE_NAME,
    MAILPIT_SERVICE_SPEC,
)
from dev_project.manifest.reader import load_manifest
from tests.fixtures.compose.mailpit_fragment import MAILPIT_COMPOSE_FRAGMENT
from tests.test_manifest_v2_reader import _minimal_v2


def _load_contract_modules() -> unittest.TestSuite:
    """Aggregate manifest/extension unit modules for CI contract job."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    modules = (
        "tests.test_manifest_v2_reader",
        "tests.test_manifest_compat",
        "tests.test_manifest_cli",
        "tests.test_manifest_migrate",
        "tests.test_manifest_locks_sync",
        "tests.test_manifest_hooks",
        "tests.test_plan_locks_preview",
        "tests.test_plan_config_coupling",
        "tests.test_manifest_database_merge",
        "tests.test_compose_fragments",
        "tests.test_extension_entry_points",
        "tests.test_prepare_registry_contract",
    )
    for module_name in modules:
        suite.addTests(loader.loadTestsFromName(module_name))
    suite.addTests(loader.loadTestsFromTestCase(ManifestExtensionContractTests))
    return suite


class ManifestExtensionContractTests(unittest.TestCase):
    """Cross-module checks for manifest v2 + compose fragments."""

    def test_v2_mailpit_services_render_golden_fragment(self):
        view = load_manifest(
            _minimal_v2(services={"mailpit": dict(MAILPIT_SERVICE_SPEC)})
        )
        ext = ExtensionHostContext(
            host=MagicMock(),
            repo_odpm_json="/tmp/odpm.json",
            manifest_services=view.services,
            manifest_schema=constants.MANIFEST_SCHEMA_V2,
        )
        block = render_compose_services_block(collect_compose_services(ext))
        self.assertEqual(block, MAILPIT_COMPOSE_FRAGMENT)

    def test_prepare_step_count_includes_compose_fragments(self):
        from dev_project.prepare.registry import BUILTIN_PREPARE_STEPS

        step_ids = [step.id for step in BUILTIN_PREPARE_STEPS]
        self.assertIn("compose.fragments", step_ids)
        self.assertLess(
            step_ids.index("compose.template"),
            step_ids.index("compose.fragments"),
        )
        self.assertLess(
            step_ids.index("compose.fragments"),
            step_ids.index("compose.generate"),
        )

    def test_mailpit_reference_spec_passes_v2_services_schema(self):
        view = load_manifest(
            _minimal_v2(services={MAILPIT_SERVICE_NAME: dict(MAILPIT_SERVICE_SPEC)})
        )
        self.assertEqual(
            view.services[MAILPIT_SERVICE_NAME],
            MAILPIT_SERVICE_SPEC,
        )

    def test_v2_service_without_image_rejected_by_schema(self):
        with self.assertRaises(ConfigError):
            load_manifest(_minimal_v2(services={"broken": {"ports": ["8025:8025"]}}))


def load_tests(loader: unittest.TestLoader, tests: unittest.TestSuite, pattern: str):
    del loader, tests, pattern
    return _load_contract_modules()


if __name__ == "__main__":
    unittest.main()
