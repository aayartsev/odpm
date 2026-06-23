"""D4 plugin API 1.1 and nested compose inheritance tests."""

from __future__ import annotations

import json
import os
import tempfile
import textwrap
import unittest
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.compose.fragments import collect_compose_services, collect_service_patches
from dev_project.dependency_resolver import NestedOdpmFragment, read_nested_odpm_fragment
from dev_project.errors import ConfigError
from dev_project.extensions.api import EXTENSION_API_VERSION, assert_extension_api_compatible
from dev_project.extensions.context import ExtensionHostContext
from dev_project.extensions.loader import resolve_plugin_api_version, validate_plugin_api
from dev_project.extensions.registry import reset_extension_registry_state
from dev_project.manifest.nested_compose import inherit_nested_compose_into_manifest
from dev_project.manifest.reader import load_manifest
from tests.fixtures.sample_plugin import sample_odpm_plugin
from tests.test_manifest_v2_reader import _minimal_v2


class ExtensionApiVersionTests(unittest.TestCase):
    def test_extension_api_1_1_is_supported(self) -> None:
        assert_extension_api_compatible("1.1")
        assert_extension_api_compatible("1.0")

    def test_unsupported_api_version_raises(self) -> None:
        with self.assertRaises(ConfigError):
            assert_extension_api_compatible("2.0", plugin_id="bad.plugin")

    def test_missing_plugin_version_defaults_to_1_0(self) -> None:
        class _LegacyPlugin:
            pass

        self.assertEqual(resolve_plugin_api_version(_LegacyPlugin()), "1.0")
        validate_plugin_api(_LegacyPlugin(), plugin_id="legacy")


class SamplePluginPatchTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_extension_registry_state()
        sample_odpm_plugin.register_sample_plugin()

    def tearDown(self) -> None:
        reset_extension_registry_state()

    def test_sample_plugin_registers_compose_service_patches(self) -> None:
        ext = ExtensionHostContext(
            host=MagicMock(),
            repo_odpm_json="/tmp/odpm.json",
        )
        patches = collect_service_patches(ext)
        self.assertIn("odoo", patches)
        self.assertEqual(
            patches["odoo"]["environment"][sample_odpm_plugin.SAMPLE_PATCH_ENV_KEY],
            EXTENSION_API_VERSION,
        )

    def test_sample_plugin_registers_mailpit_compose_service(self) -> None:
        ext = ExtensionHostContext(
            host=MagicMock(),
            repo_odpm_json="/tmp/odpm.json",
        )
        services = collect_compose_services(ext)
        self.assertIn("mailpit", services)


class NestedComposeInheritTests(unittest.TestCase):
    def test_read_nested_fragment_extracts_services(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir:
            manifest_path = os.path.join(project_dir, constants.PROJECT_CONFIG_FILE_NAME)
            with open(manifest_path, "w", encoding="utf-8") as handle:
                json.dump(
                    _minimal_v2(
                        services={"mailpit": {"image": "axllent/mailpit"}},
                    ),
                    handle,
                )
            fragment = read_nested_odpm_fragment(project_dir)
            self.assertIsNotNone(fragment)
            assert fragment is not None
            self.assertIn("mailpit", fragment.services or {})

    def test_host_manifest_wins_over_nested_services(self) -> None:
        config = MagicMock()
        host_view = load_manifest(
            _minimal_v2(
                services={"mailpit": {"image": "host/mailpit:custom"}},
            )
        )
        config.bootstrap.manifest_view = host_view
        config.bootstrap.raw_odpm_json = dict(host_view.raw_normalized)
        nested = NestedOdpmFragment(
            dependencies=[],
            requirements_txt=[],
            odoo_version=None,
            python_version=None,
            source_path="/tmp/dep/odpm.json",
            services={"mailpit": {"image": "nested/mailpit"}},
        )
        inherit_nested_compose_into_manifest(config, [nested])
        view = config.bootstrap.manifest_view
        self.assertIsNotNone(view)
        assert view is not None
        self.assertEqual(view.services["mailpit"]["image"], "host/mailpit:custom")

    def test_nested_service_patches_merge_before_host(self) -> None:
        config = MagicMock()
        host_view = load_manifest(
            _minimal_v2(
                service_patches={
                    "odoo": {"environment": {"HOST_ONLY": "1"}},
                }
            )
        )
        config.bootstrap.manifest_view = host_view
        config.bootstrap.raw_odpm_json = dict(host_view.raw_normalized)
        nested = NestedOdpmFragment(
            dependencies=[],
            requirements_txt=[],
            odoo_version=None,
            python_version=None,
            source_path="/tmp/dep/odpm.json",
            service_patches={
                "odoo": {"environment": {"NESTED_ONLY": "1"}},
            },
        )
        inherit_nested_compose_into_manifest(config, [nested])
        env = config.bootstrap.manifest_view.service_patches["odoo"]["environment"]
        if isinstance(env, list):
            env_map = {
                item.split("=", 1)[0]: item.split("=", 1)[1]
                for item in env
                if isinstance(item, str) and "=" in item
            }
        else:
            env_map = dict(env)
        self.assertEqual(env_map["HOST_ONLY"], "1")
        self.assertEqual(env_map["NESTED_ONLY"], "1")


class LocalPluginApiValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_extension_registry_state()
        from dev_project.extensions.local import reset_local_plugins_state

        reset_local_plugins_state()

    def tearDown(self) -> None:
        reset_extension_registry_state()
        from dev_project.extensions.local import reset_local_plugins_state

        reset_local_plugins_state()

    def test_local_plugin_with_unsupported_api_version_raises(self) -> None:
        from dev_project.extensions.local import load_project_local_plugins

        plugin_source = textwrap.dedent(
            '''
            EXTENSION_API_VERSION = "9.9"
            '''
        )
        with tempfile.TemporaryDirectory() as project_dir:
            plugins_dir = os.path.join(project_dir, ".odpm", "plugins")
            os.makedirs(plugins_dir)
            with open(os.path.join(plugins_dir, "bad.py"), "w", encoding="utf-8") as handle:
                handle.write(plugin_source)
            with self.assertRaises(ConfigError):
                load_project_local_plugins(project_dir)


if __name__ == "__main__":
    unittest.main()
