"""Tests for manifest ``service_sources`` (schema, slice merge, ManifestView)."""

from __future__ import annotations

import unittest

from dev_project import constants
from dev_project.config.transforms.env_substitution import (
    EnvResolver,
    expand_env_in_service_sources,
)
from dev_project.errors import ConfigError
from dev_project.manifest.reader import load_manifest
from dev_project.manifest.schema import validate_manifest_v2
from dev_project.manifest.scenario_overrides import (
    merge_manifest_slice,
    resolve_effective_manifest_slice,
    ScenarioManifestSlice,
)
from dev_project.manifest.service_sources import (
    merge_service_sources,
    normalize_service_sources,
)
from tests.test_manifest_v2_reader import _minimal_v2


class ServiceSourcesNormalizeTests(unittest.TestCase):
    def test_none_and_empty_return_none(self):
        self.assertIsNone(normalize_service_sources(None))
        self.assertIsNone(normalize_service_sources({}))

    def test_valid_names_and_links(self):
        result = normalize_service_sources(
            {
                "autoparts_env": "https://github.com/org/repo.git 17.0",
                "fixtures": "file:///opt/fixtures",
            }
        )
        self.assertEqual(
            result,
            {
                "autoparts_env": "https://github.com/org/repo.git 17.0",
                "fixtures": "file:///opt/fixtures",
            },
        )

    def test_rejects_invalid_key(self):
        with self.assertRaises(ConfigError):
            normalize_service_sources({"Autoparts": "https://example.com/repo.git"})

    def test_rejects_empty_link(self):
        with self.assertRaises(ConfigError):
            normalize_service_sources({"autoparts_env": "  "})


class ServiceSourcesMergeTests(unittest.TestCase):
    def test_overlay_replaces_by_name(self):
        base = {"autoparts_env": "https://github.com/org/a.git 17.0", "fixtures": "file:///a"}
        overlay = {"autoparts_env": "https://github.com/org/b.git 18.0"}
        merged = merge_service_sources(base, overlay)
        self.assertEqual(
            merged,
            {
                "autoparts_env": "https://github.com/org/b.git 18.0",
                "fixtures": "file:///a",
            },
        )

    def test_scenario_overlay_replace_by_name(self):
        raw = _minimal_v2(
            service_sources={
                "autoparts_env": "https://github.com/org/base.git 17.0",
            },
            scenarios={
                "developer": {
                    "service_sources": {
                        "autoparts_env": "https://github.com/org/dev.git 17.0",
                    }
                }
            },
        )
        dev = resolve_effective_manifest_slice(raw, constants.DEVELOPER_SCENARIO)
        server = resolve_effective_manifest_slice(raw, constants.SERVER_SCENARIO)
        self.assertEqual(
            dev.service_sources,
            {"autoparts_env": "https://github.com/org/dev.git 17.0"},
        )
        self.assertEqual(
            server.service_sources,
            {"autoparts_env": "https://github.com/org/base.git 17.0"},
        )

    def test_merge_slice_combines_sources(self):
        base = ScenarioManifestSlice(
            service_sources={"a": "https://example.com/a.git"},
        )
        overlay = ScenarioManifestSlice(
            service_sources={"b": "https://example.com/b.git"},
        )
        merged = merge_manifest_slice(base, overlay)
        self.assertEqual(
            merged.service_sources,
            {
                "a": "https://example.com/a.git",
                "b": "https://example.com/b.git",
            },
        )


class ServiceSourcesSchemaTests(unittest.TestCase):
    def test_schema_accepts_service_sources_and_service_source_field(self):
        raw = _minimal_v2(
            service_sources={
                "autoparts_env": "https://github.com/org/autoparts-env.git 17.0",
            },
            services={
                "armtek_test": {
                    "source": "autoparts_env",
                    "image": "autoparts_env:emulator",
                    "volumes": ["${@source:autoparts_env}/data:/data:Z"],
                }
            },
        )
        validate_manifest_v2(raw)

    def test_schema_rejects_invalid_service_source_name(self):
        raw = _minimal_v2(
            service_sources={
                "AutopartsEnv": "https://github.com/org/repo.git",
            },
        )
        with self.assertRaises(ConfigError):
            validate_manifest_v2(raw)

    def test_unknown_service_source_reference_raises(self):
        from dev_project.manifest.scenario_overrides import validate_scenario_manifest

        raw = _minimal_v2(
            services={
                "armtek_test": {
                    "source": "missing_env",
                    "image": "autoparts_env:emulator",
                }
            },
        )
        with self.assertRaises(ConfigError):
            validate_scenario_manifest(raw)

    def test_service_source_reference_validates_when_declared(self):
        from dev_project.manifest.scenario_overrides import validate_scenario_manifest

        raw = _minimal_v2(
            service_sources={
                "autoparts_env": "https://github.com/org/autoparts-env.git 17.0",
            },
            services={
                "armtek_test": {
                    "source": "autoparts_env",
                    "image": "autoparts_env:emulator",
                }
            },
        )
        validate_scenario_manifest(raw)


class ServiceSourcesLoadManifestTests(unittest.TestCase):
    def test_manifest_view_exposes_service_sources(self):
        view = load_manifest(
            _minimal_v2(
                service_sources={
                    "autoparts_env": "https://github.com/org/autoparts-env.git 17.0",
                },
            ),
        )
        self.assertEqual(
            view.service_sources,
            {"autoparts_env": "https://github.com/org/autoparts-env.git 17.0"},
        )
        self.assertEqual(
            view.scenario_slice.service_sources,
            {"autoparts_env": "https://github.com/org/autoparts-env.git 17.0"},
        )

    def test_env_expansion_on_service_sources_at_load(self):
        view = load_manifest(
            _minimal_v2(
                service_sources={
                    "autoparts_env": "https://${GIT_HOST}/org/autoparts-env.git 17.0",
                },
            ),
            env_resolver=EnvResolver.from_sources(
                process_environ={},
                project_dotenv={"GIT_HOST": "git.company.example"},
            ),
        )
        self.assertEqual(
            view.service_sources,
            {"autoparts_env": "https://git.company.example/org/autoparts-env.git 17.0"},
        )


class ServiceSourcesEnvExpandTests(unittest.TestCase):
    def test_expand_env_in_service_sources(self):
        resolver = EnvResolver.from_sources(
            process_environ={"GIT_HOST": "git.example.com"},
            project_dotenv={},
        )
        expanded = expand_env_in_service_sources(
            {"repo": "https://${GIT_HOST}/org/repo.git 19.0"},
            resolver=resolver,
        )
        self.assertEqual(
            expanded,
            {"repo": "https://git.example.com/org/repo.git 19.0"},
        )


if __name__ == "__main__":
    unittest.main()
