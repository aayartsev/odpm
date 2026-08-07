"""Tests for manifest odoo_conf overrides and policy."""

from __future__ import annotations

import unittest

from dev_project import constants
from dev_project.config.transforms.env_substitution import EnvResolver
from dev_project.errors import ConfigError
from dev_project.manifest.odoo_conf import merge_odoo_conf_sections, odoo_conf_from_manifest
from dev_project.manifest.odoo_conf_policy import validate_manifest_odoo_conf
from dev_project.manifest.reader import ManifestView, load_manifest
from tests.test_manifest_v2_reader import _minimal_v2


class ManifestOdooConfPolicyTests(unittest.TestCase):
    def test_validate_accepts_allowed_option(self):
        validate_manifest_odoo_conf(
            {
                "odoo_conf": {
                    "options": {
                        "proxy_mode": "True",
                        "workers": "2",
                    }
                }
            }
        )

    def test_validate_rejects_reserved_addons_path(self):
        with self.assertRaises(ConfigError) as ctx:
            validate_manifest_odoo_conf(
                {
                    "odoo_conf": {
                        "options": {
                            "addons_path": "/tmp/addons",
                        }
                    }
                }
            )
        self.assertIn("addons_path", str(ctx.exception))

    def test_load_manifest_v2_rejects_reserved_key(self):
        with self.assertRaises(ConfigError):
            load_manifest(
                _minimal_v2(
                    odoo_conf={
                        "options": {
                            "db_host": "custom-db",
                        }
                    }
                )
            )

    def test_load_manifest_v2_accepts_extra_odoo_conf_sections(self):
        view = load_manifest(
            _minimal_v2(
                odoo_conf={
                    "options": {"proxy_mode": "True"},
                    "redis_server": {
                        "host": "redis",
                        "port": 6379,
                        "password": "secret",
                    },
                    "s3_server": {
                        "endpoint": "minio:9000",
                        "secret_key": "minio-secret",
                    },
                }
            )
        )
        self.assertEqual(view.odoo_conf["options"]["proxy_mode"], "True")
        self.assertEqual(view.odoo_conf["redis_server"]["port"], 6379)
        self.assertEqual(view.odoo_conf["s3_server"]["endpoint"], "minio:9000")

    def test_load_manifest_expands_secret_and_service_in_extra_sections(self):
        from dev_project.compose.service_names import ComposeNamingContext

        resolver = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={},
            secrets={"redis_password": "pw", "minio_root_password": "msecret"},
            compose_naming=ComposeNamingContext(
                compose_prefix=None,
                compose_project_name=None,
                postgres_service_name="db",
                odoo_service_name="odoo",
                postgres_volume_name="postgres-data",
            ),
        )
        view = load_manifest(
            _minimal_v2(
                odoo_conf={
                    "redis_server": {
                        "host": "${@service:redis}",
                        "password": "${@secret:redis_password}",
                    },
                    "s3_server": {
                        "endpoint": "${@service:minio}:9000",
                        "secret_key": "${@secret:minio_root_password}",
                    },
                }
            ),
            env_resolver=resolver,
        )
        self.assertEqual(view.odoo_conf["redis_server"]["host"], "redis")
        self.assertEqual(view.odoo_conf["redis_server"]["password"], "pw")
        self.assertEqual(view.odoo_conf["s3_server"]["endpoint"], "minio:9000")
        self.assertEqual(view.odoo_conf["s3_server"]["secret_key"], "msecret")

    def test_merge_extra_sections_with_disk(self):
        merged = merge_odoo_conf_sections(
            {
                "options": {"proxy_mode": "False"},
                "redis_server": {"host": "old", "port": "6379"},
            },
            {
                "redis_server": {"host": "redis", "password": "pw"},
                "s3_server": {"endpoint": "minio:9000"},
            },
        )
        self.assertEqual(
            merged,
            {
                "options": {"proxy_mode": "False"},
                "redis_server": {
                    "host": "redis",
                    "port": "6379",
                    "password": "pw",
                },
                "s3_server": {"endpoint": "minio:9000"},
            },
        )


class ManifestOdooConfEnvExpandTests(unittest.TestCase):
    def test_load_manifest_expands_env_in_odoo_conf(self):
        resolver = EnvResolver.from_sources(
            process_environ={"PREVIEW_HOSTNAME": "pr-42.preview.local"},
            project_dotenv={},
        )
        view = load_manifest(
            _minimal_v2(
                odoo_conf={
                    "options": {
                        "dbfilter": "^${PREVIEW_HOSTNAME}$",
                    }
                }
            ),
            env_resolver=resolver,
        )
        self.assertEqual(
            view.odoo_conf,
            {"options": {"dbfilter": "^pr-42.preview.local$"}},
        )

    def test_load_manifest_missing_env_var_raises(self):
        resolver = EnvResolver.from_sources(process_environ={}, project_dotenv={})
        with self.assertRaises(ConfigError) as ctx:
            load_manifest(
                _minimal_v2(
                    odoo_conf={
                        "options": {
                            "dbfilter": "^${PREVIEW_HOSTNAME}$",
                        }
                    }
                ),
                env_resolver=resolver,
            )
        self.assertIn("PREVIEW_HOSTNAME", str(ctx.exception))

    def test_load_manifest_applies_scenario_odoo_conf_overlay(self):
        view = load_manifest(
            _minimal_v2(
                requires_odpm="4.6.0",
                odoo_conf={"options": {"workers": "0"}},
                scenarios={
                    "server": {"odoo_conf": {"options": {"workers": "8"}}},
                },
            ),
            active_scenario=constants.SERVER_SCENARIO,
        )
        self.assertEqual(view.odoo_conf, {"options": {"workers": "8"}})


class ManifestOdooConfMergeTests(unittest.TestCase):
    def test_merge_odoo_conf_sections_overrides_disk_values(self):
        merged = merge_odoo_conf_sections(
            {"options": {"proxy_mode": "False", "log_level": "info"}},
            {"options": {"proxy_mode": "True"}},
        )
        self.assertEqual(
            merged,
            {"options": {"proxy_mode": "True", "log_level": "info"}},
        )

    def test_odoo_conf_from_manifest_returns_none_when_absent(self):
        view = ManifestView(
            manifest_schema=2,
            requires_odpm="4.5.0",
            raw_normalized={},
        )
        self.assertIsNone(odoo_conf_from_manifest(view))


if __name__ == "__main__":
    unittest.main()
