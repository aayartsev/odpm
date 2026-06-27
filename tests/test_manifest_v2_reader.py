"""Tests for manifest v2 schema validation and dual-read loader."""

from __future__ import annotations

import unittest

from dev_project import constants
from dev_project.config.transforms.env_substitution import EnvResolver
from dev_project.errors import ConfigError
from dev_project.manifest.reader import (
    ManifestView,
    load_manifest,
    normalize_v2_to_flat,
)
from dev_project.manifest.schema import manifest_schema_v1, manifest_schema_v2, validate_manifest_v1


def _minimal_v2(**overrides) -> dict:
    payload = {
        "manifest_schema": 2,
        "requires_odpm": "4.4",
        "platform": {"git": "https://github.com/odoo/odoo.git 19.0"},
        "python": "3.12",
        "distro": {"name": "debian", "version": "13"},
        "postgres": "15",
        "dependencies": [],
        "requirements": [],
    }
    payload.update(overrides)
    return payload


class ManifestSchemaFilesTests(unittest.TestCase):
    def test_schema_files_load(self):
        self.assertEqual(manifest_schema_v1()["title"], "odpm.json manifest v1 (flat)")
        self.assertEqual(manifest_schema_v2()["properties"]["manifest_schema"]["const"], 2)


class NormalizeV2Tests(unittest.TestCase):
    def test_maps_nested_fields_to_flat_keys(self):
        raw = _minimal_v2(
            platform={
                "git": "https://github.com/odoo/odoo.git 19.0",
                "build_date": "20251223",
            },
            dependencies=["https://github.com/OCA/web.git 19.0"],
            requirements=["requests==2.31.0"],
        )
        flat = normalize_v2_to_flat(raw)
        self.assertEqual(flat["odoo_git_link"], "https://github.com/odoo/odoo.git 19.0")
        self.assertEqual(flat["odoo_build_date"], "20251223")
        self.assertEqual(flat["python_version"], "3.12")
        self.assertEqual(flat["distro_name"], "debian")
        self.assertEqual(flat["distro_version"], "13")
        self.assertEqual(flat["postgres_version"], "15")
        self.assertEqual(flat["odoo_version"], "19.0")
        self.assertEqual(flat["dependencies"], ["https://github.com/OCA/web.git 19.0"])
        self.assertEqual(flat["requirements_txt"], ["requests==2.31.0"])

    def test_explicit_odoo_version_overrides_git_branch(self):
        flat = normalize_v2_to_flat(_minimal_v2(odoo_version="18.0"))
        self.assertEqual(flat["odoo_version"], "18.0")


class LoadManifestTests(unittest.TestCase):
    def test_v1_flat_returns_copy_of_raw(self):
        raw = {
            "odpm_version": "4.0",
            "odoo_version": "17.0",
            "python_version": "3.12",
        }
        view = load_manifest(raw)
        self.assertIsInstance(view, ManifestView)
        self.assertEqual(view.manifest_schema, constants.MANIFEST_SCHEMA_V1)
        self.assertEqual(view.raw_normalized, raw)
        self.assertIsNot(view.raw_normalized, raw)

    def test_v1_explicit_manifest_schema_reads_odpm_version(self):
        view = load_manifest(
            {"manifest_schema": 1, "odpm_version": "4.0", "odoo_version": "17.0"}
        )
        self.assertEqual(view.manifest_schema, constants.MANIFEST_SCHEMA_V1)

    def test_v2_valid_manifest(self):
        raw = _minimal_v2(
            hooks={"post_prepare": [["echo", "hi"]]},
            services={"mailpit": {"image": "axllent/mailpit"}},
            locks={"git": {"https://github.com/OCA/web.git 19.0": "abc123"}},
            developing={"git": "https://github.com/acme/demo.git"},
            database={"language": "ru_RU", "country": "RU"},
        )
        view = load_manifest(raw)
        self.assertEqual(view.manifest_schema, constants.MANIFEST_SCHEMA_V2)
        self.assertEqual(view.requires_odpm, "4.4")
        self.assertEqual(view.developing_git, "https://github.com/acme/demo.git")
        self.assertEqual(view.hooks, {"post_prepare": [["echo", "hi"]]})
        self.assertEqual(view.services, {"mailpit": {"image": "axllent/mailpit"}})
        self.assertEqual(
            view.locks,
            {"git": {"https://github.com/OCA/web.git 19.0": "abc123"}},
        )
        self.assertEqual(view.raw_normalized["odoo_version"], "19.0")
        self.assertEqual(view.source_raw["database"]["language"], "ru_RU")

    def test_v2_invalid_schema_raises(self):
        broken = _minimal_v2()
        del broken["platform"]
        with self.assertRaises(ConfigError):
            load_manifest(broken)

    def test_v2_unknown_top_level_key_raises(self):
        broken = _minimal_v2(extra_field="nope")
        with self.assertRaises(ConfigError):
            load_manifest(broken)

    def test_v2_invalid_service_spec_raises(self):
        with self.assertRaises(ConfigError):
            load_manifest(_minimal_v2(services={"mailpit": {"ports": ["8025:8025"]}}))

    def test_v2_reserved_service_in_services_raises(self):
        with self.assertRaises(ConfigError):
            load_manifest(
                _minimal_v2(services={"odoo": {"image": "odoo:dev", "ports": []}})
            )

    def test_v2_service_patches_and_command_on_sidecar(self):
        raw = _minimal_v2(
            services={
                "worker": {
                    "image": "busybox:latest",
                    "command": ["sh", "-c", "sleep infinity"],
                    "entrypoint": ["sh"],
                }
            },
            service_patches={
                "odoo": {"environment": {"WORKER_ENABLED": "1"}},
            },
        )
        view = load_manifest(raw)
        self.assertEqual(
            view.services,
            {
                "worker": {
                    "image": "busybox:latest",
                    "command": ["sh", "-c", "sleep infinity"],
                    "entrypoint": ["sh"],
                }
            },
        )
        self.assertEqual(
            view.service_patches,
            {"odoo": {"environment": {"WORKER_ENABLED": "1"}}},
        )

    def test_v2_services_expand_env_when_resolver_provided(self):
        resolver = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={"DATA_DIR": "/opt/data"},
        )
        raw = _minimal_v2(
            services={
                "worker": {
                    "image": "busybox:latest",
                    "volumes": ["${DATA_DIR}:/data"],
                }
            },
            service_patches={
                "odoo": {"volumes": ["${DATA_DIR}:/mnt"]},
            },
        )
        view = load_manifest(raw, env_resolver=resolver)
        self.assertEqual(
            view.services,
            {
                "worker": {
                    "image": "busybox:latest",
                    "volumes": ["/opt/data:/data"],
                }
            },
        )
        self.assertEqual(
            view.service_patches,
            {"odoo": {"volumes": ["/opt/data:/mnt"]}},
        )

    def test_v2_services_user_and_tty_allowed(self):
        raw = _minimal_v2(
            services={
                "sidecar": {
                    "image": "busybox:latest",
                    "user": "root",
                    "tty": True,
                }
            }
        )
        view = load_manifest(raw)
        self.assertEqual(
            view.services,
            {
                "sidecar": {
                    "image": "busybox:latest",
                    "user": "root",
                    "tty": True,
                }
            },
        )

    def test_v1_validate_accepts_minimal_flat_manifest(self):
        validate_manifest_v1(
            {
                "odpm_version": constants.MANIFEST_V1_CONTRACT_LINE,
                "odoo_version": "17.0",
            }
        )

    def test_v1_unsupported_contract_still_raises(self):
        with self.assertRaises(ConfigError):
            load_manifest({"odpm_version": "2.0"})

    def test_v2_scenario_overlay_wires_effective_odoo_conf_and_requirements(self):
        raw = _minimal_v2(
            requires_odpm="4.6.0",
            requirements=["requests==2.31.0"],
            odoo_conf={"options": {"proxy_mode": "True", "workers": "0"}},
            scenarios={
                "server": {
                    "requirements": ["gunicorn"],
                    "odoo_conf": {"options": {"workers": "4"}},
                }
            },
        )
        dev = load_manifest(raw, active_scenario=constants.DEVELOPER_SCENARIO)
        server = load_manifest(raw, active_scenario=constants.SERVER_SCENARIO)
        self.assertEqual(dev.raw_normalized["requirements_txt"], ["requests==2.31.0"])
        self.assertEqual(
            server.raw_normalized["requirements_txt"],
            ["requests==2.31.0", "gunicorn"],
        )
        self.assertEqual(dev.odoo_conf, {"options": {"proxy_mode": "True", "workers": "0"}})
        self.assertEqual(
            server.odoo_conf,
            {"options": {"proxy_mode": "True", "workers": "4"}},
        )
        self.assertIsNotNone(server.scenario_slice)
        self.assertEqual(server.scenario_slice.requirements, ["requests==2.31.0", "gunicorn"])

    def test_v2_load_rejects_reserved_odoo_conf_in_scenario_overlay(self):
        with self.assertRaises(ConfigError):
            load_manifest(
                _minimal_v2(
                    requires_odpm="4.6.0",
                    scenarios={
                        "server": {
                            "odoo_conf": {"options": {"db_host": "evil"}},
                        }
                    },
                ),
                active_scenario=constants.SERVER_SCENARIO,
            )


class OdpmJsonReaderIntegrationTests(unittest.TestCase):
    def test_get_odpm_settings_stores_manifest_view_and_normalized_flat(self):
        import json
        import tempfile
        from unittest.mock import MagicMock

        from dev_project.config.manifests.odpm_json_reader import OdpmJsonReader

        with tempfile.TemporaryDirectory() as tmp:
            repo = f"{tmp}/developing/odpm.json"
            import os

            os.makedirs(os.path.dirname(repo), exist_ok=True)
            with open(repo, "w", encoding="utf-8") as handle:
                json.dump(_minimal_v2(), handle)

            config = MagicMock()
            config.repo_odpm_json = repo
            config.project_odpm_json = f"{tmp}/odpm.json"
            config.bootstrap = MagicMock()
            config.env_resolver = MagicMock()
            config.env_resolver.resolve.return_value = None
            config.user_env = MagicMock()
            config.user_env.odpm_scenario = constants.DEVELOPER_SCENARIO

            OdpmJsonReader(config, rewrite_odpm_json=MagicMock()).get_odpm_settings()

            self.assertIsNotNone(config.bootstrap.manifest_view)
            self.assertEqual(
                config.bootstrap.manifest_view.manifest_schema,
                constants.MANIFEST_SCHEMA_V2,
            )
            self.assertEqual(
                config._raw_odpm_json["odoo_git_link"],
                "https://github.com/odoo/odoo.git 19.0",
            )


if __name__ == "__main__":
    unittest.main()
