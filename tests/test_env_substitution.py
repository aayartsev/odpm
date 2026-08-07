"""Tests for manifest ${VAR} / ${VAR:-default} substitution."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock
from unittest.mock import patch

from dev_project import constants
from dev_project.config.transforms.env_substitution import (
    ODPM_JSON_ENV_EXPAND_FIELDS,
    EnvResolver,
    collect_secret_refs_in_value,
    expand_env_in_compose_service_map,
    expand_env_in_json,
    expand_env_string,
    inject_service_source_paths,
    merged_subprocess_environ,
    with_secrets,
)
from dev_project.errors import ConfigError


class EnvResolverTests(unittest.TestCase):
    def test_resolve_prefers_process_environ_over_project_dotenv(self):
        resolver = EnvResolver.from_sources(
            process_environ={"GIT_HOST": "from-process"},
            project_dotenv={"GIT_HOST": "from-dotenv"},
        )
        self.assertEqual(resolver.resolve("GIT_HOST"), "from-process")

    def test_resolve_falls_back_to_project_dotenv(self):
        resolver = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={"PLATFORM_DIR": "/tmp/platform"},
        )
        self.assertEqual(resolver.resolve("PLATFORM_DIR"), "/tmp/platform")

    def test_resolve_returns_none_when_unset(self):
        resolver = EnvResolver.from_sources(process_environ={}, project_dotenv={})
        self.assertIsNone(resolver.resolve("MISSING"))

    def test_from_user_env_uses_project_dotenv_dict(self):
        user_env = mock.MagicMock()
        user_env.project_dotenv_dict.return_value = {"PLATFORM_DIR": "/tmp/platform"}
        user_env.compose_prefix = None
        user_env.compose_project_name = None
        user_env.postgres_service_name = "db"
        user_env.odoo_service_name = "odoo"
        user_env.postgres_volume_name = "postgres-data"
        resolver = EnvResolver.from_user_env(
            user_env,
            process_environ={"GIT_HOST": "from-process"},
        )
        self.assertEqual(resolver.resolve("GIT_HOST"), "from-process")
        self.assertEqual(resolver.resolve("PLATFORM_DIR"), "/tmp/platform")
        self.assertIsNotNone(resolver.compose_naming)
        self.assertEqual(resolver.compose_naming.postgres_service_name, "db")
        user_env.project_dotenv_dict.assert_called_once_with()

    def test_from_user_env_wires_compose_prefix_naming(self):
        user_env = mock.MagicMock()
        user_env.project_dotenv_dict.return_value = {}
        user_env.compose_prefix = "acme-"
        user_env.compose_project_name = "acme"
        user_env.postgres_service_name = "acme-db"
        user_env.odoo_service_name = "acme-odoo"
        user_env.postgres_volume_name = "acme-postgres-data"
        resolver = EnvResolver.from_user_env(user_env, process_environ={})
        self.assertEqual(resolver.compose_naming.postgres_service_name, "acme-db")
        self.assertEqual(resolver.compose_naming.odoo_service_name, "acme-odoo")
        self.assertEqual(
            expand_env_string(
                "${@service:db}",
                resolver,
                field_path="services.x.environment.DB_HOST",
            ),
            "acme-db",
        )

    def test_from_user_env_sees_home_only_key_after_layered_merge(self):
        from dev_project.host.user_env import CreateUserEnvironment
        from tests.test_user_env_bootstrap import (
            _home_env_path,
            _make_pd_manager,
            _write_minimal_env_file,
        )

        with tempfile.TemporaryDirectory() as project_dir, tempfile.TemporaryDirectory() as home_dir:
            _write_minimal_env_file(
                _home_env_path(home_dir),
                extra_lines=["GIT_HOST=git.home.example"],
            )
            Path(os.path.join(project_dir, constants.ENV_FILE_NAME)).write_text(
                "ODOO_PLATFORM_DIR=/work/odoo/19.0\n",
                encoding="utf-8",
            )
            pd_manager = _make_pd_manager(project_dir, home_dir=home_dir)
            with patch.dict(os.environ, {"HOME": home_dir}, clear=False):
                user_env = CreateUserEnvironment(pd_manager)
            resolver = EnvResolver.from_user_env(user_env, process_environ={})
            self.assertEqual(resolver.resolve("GIT_HOST"), "git.home.example")
            self.assertEqual(resolver.resolve("ODOO_PLATFORM_DIR"), "/work/odoo/19.0")
            self.assertIsNotNone(resolver.compose_naming)


class ExpandEnvStringTests(unittest.TestCase):
    def setUp(self) -> None:
        self.resolver = EnvResolver.from_sources(
            process_environ={"GIT_HOST": "git.company.example"},
            project_dotenv={"ODOO_PLATFORM_DIR": "/home/dev/odoo/19.0"},
        )

    def test_expands_file_url_from_dotenv(self):
        result = expand_env_string(
            "file://${ODOO_PLATFORM_DIR}",
            self.resolver,
            field_path="odoo_git_link",
        )
        self.assertEqual(result, "file:///home/dev/odoo/19.0")

    def test_expands_git_url_from_process_environ(self):
        result = expand_env_string(
            "https://${GIT_HOST}/company/extra.git 17.0",
            self.resolver,
            field_path="dependencies[]",
        )
        self.assertEqual(
            result,
            "https://git.company.example/company/extra.git 17.0",
        )

    def test_expands_default_when_var_missing(self):
        result = expand_env_string(
            "file://${MISSING:-/default/path}",
            self.resolver,
            field_path="developing_project",
        )
        self.assertEqual(result, "file:///default/path")

    def test_missing_var_without_default_raises_config_error(self):
        with self.assertRaises(ConfigError) as ctx:
            expand_env_string(
                "file://${MISSING}",
                self.resolver,
                field_path="odoo_git_link",
            )
        self.assertIn("MISSING", str(ctx.exception))
        self.assertIn("odoo_git_link", str(ctx.exception))

    def test_dollar_dollar_escape(self):
        result = expand_env_string(
            "cost is $$100",
            self.resolver,
            field_path="odoo_git_link",
        )
        self.assertEqual(result, "cost is $100")

    def test_dollar_escape_before_expansion(self):
        result = expand_env_string(
            "file://$$${ODOO_PLATFORM_DIR}",
            self.resolver,
            field_path="odoo_git_link",
        )
        self.assertEqual(result, "file://$/home/dev/odoo/19.0")

    def test_string_without_dollar_unchanged(self):
        result = expand_env_string(
            "file:///fixed/path",
            self.resolver,
            field_path="odoo_git_link",
        )
        self.assertEqual(result, "file:///fixed/path")

    def test_expands_source_reference_from_resolver(self):
        resolver = EnvResolver.from_sources(
            process_environ={"ODPM_SOURCE_AUTOPARTS_ENV": "/opt/autoparts"},
            project_dotenv={},
        )
        result = expand_env_string(
            "${@source:autoparts_env}/data",
            resolver,
            field_path="services.armtek.volumes[]",
        )
        self.assertEqual(result, "/opt/autoparts/data")

    def test_missing_source_raises_config_error(self):
        with self.assertRaises(ConfigError) as ctx:
            expand_env_string(
                "${@source:autoparts_env}/data",
                self.resolver,
                field_path="services.armtek.volumes[]",
            )
        self.assertIn("autoparts_env", str(ctx.exception))

    def test_allow_unresolved_source_preserves_token(self):
        result = expand_env_string(
            "${@source:autoparts_env}/data",
            self.resolver,
            field_path="services.armtek.volumes[]",
            allow_unresolved_source=True,
        )
        self.assertEqual(result, "${@source:autoparts_env}/data")

    def test_source_and_var_in_same_string(self):
        resolver = EnvResolver.from_sources(
            process_environ={"ODPM_SOURCE_AUTOPARTS_ENV": "/opt/autoparts"},
            project_dotenv={"DATA_SUBDIR": "data"},
        )
        result = expand_env_string(
            "${@source:autoparts_env}/${DATA_SUBDIR}",
            resolver,
            field_path="services.armtek.volumes[]",
        )
        self.assertEqual(result, "/opt/autoparts/data")


class SourceEnvKeyTests(unittest.TestCase):
    def test_source_env_key_uppercases_name(self):
        from dev_project.manifest.service_sources import source_env_key

        self.assertEqual(source_env_key("autoparts_env"), "ODPM_SOURCE_AUTOPARTS_ENV")


class InjectServiceSourcePathsTests(unittest.TestCase):
    def test_inject_adds_odpm_source_keys(self):
        from dev_project.config.transforms.env_substitution import (
            inject_service_source_paths,
        )

        base = EnvResolver.from_sources(process_environ={}, project_dotenv={})
        injected = inject_service_source_paths(
            base,
            {"autoparts_env": "/opt/autoparts"},
        )
        self.assertEqual(
            injected.resolve("ODPM_SOURCE_AUTOPARTS_ENV"),
            "/opt/autoparts",
        )

    def test_inject_preserves_compose_naming(self):
        from dev_project.compose.service_names import resolve_compose_naming
        from dev_project.config.transforms.env_substitution import (
            inject_service_source_paths,
        )

        naming = resolve_compose_naming(
            compose_prefix_raw="acme",
            legacy_postgres_service_name="db",
        )
        base = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={},
            compose_naming=naming,
        )
        injected = inject_service_source_paths(
            base,
            {"autoparts_env": "/opt/autoparts"},
        )
        self.assertIs(injected.compose_naming, naming)
        self.assertEqual(
            injected.resolve("ODPM_SOURCE_AUTOPARTS_ENV"),
            "/opt/autoparts",
        )


class ExpandServiceRefTests(unittest.TestCase):
    def _naming(self, *, prefix: str | None = "acme", legacy_db: str = "db"):
        from dev_project.compose.service_names import resolve_compose_naming

        return resolve_compose_naming(
            compose_prefix_raw=prefix,
            legacy_postgres_service_name=legacy_db,
        )

    def test_expands_db_and_odoo_with_prefix(self):
        resolver = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={},
            compose_naming=self._naming(prefix="acme"),
        )
        self.assertEqual(
            expand_env_string(
                "${@service:db}",
                resolver,
                field_path="services.x.environment.DB_HOST",
            ),
            "acme-db",
        )
        self.assertEqual(
            expand_env_string(
                "http://${@service:odoo}:8069",
                resolver,
                field_path="services.x.environment.ODOO_URL",
            ),
            "http://acme-odoo:8069",
        )

    def test_sidecar_identity_unchanged(self):
        resolver = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={},
            compose_naming=self._naming(prefix="acme"),
        )
        self.assertEqual(
            expand_env_string(
                "${@service:mailpit}",
                resolver,
                field_path="services.x.environment.PEER",
            ),
            "mailpit",
        )

    def test_no_prefix_keeps_logical_db(self):
        resolver = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={},
            compose_naming=self._naming(prefix=None),
        )
        self.assertEqual(
            expand_env_string(
                "${@service:db}",
                resolver,
                field_path="services.x.environment.DB_HOST",
            ),
            "db",
        )

    def test_legacy_postgres_service_name(self):
        resolver = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={},
            compose_naming=self._naming(prefix=None, legacy_db="pg"),
        )
        self.assertEqual(
            expand_env_string(
                "${@service:db}",
                resolver,
                field_path="services.x.environment.DB_HOST",
            ),
            "pg",
        )

    def test_missing_naming_raises_without_allow_flag(self):
        resolver = EnvResolver.from_sources(process_environ={}, project_dotenv={})
        with self.assertRaises(ConfigError) as ctx:
            expand_env_string(
                "${@service:db}",
                resolver,
                field_path="services.x.environment.DB_HOST",
            )
        self.assertIn("db", str(ctx.exception))
        self.assertIn("services.x.environment.DB_HOST", str(ctx.exception))

    def test_allow_unresolved_service_preserves_token(self):
        resolver = EnvResolver.from_sources(process_environ={}, project_dotenv={})
        result = expand_env_string(
            "${@service:db}",
            resolver,
            field_path="services.x.environment.DB_HOST",
            allow_unresolved_service=True,
        )
        self.assertEqual(result, "${@service:db}")

    def test_dollar_escape_with_service_ref(self):
        resolver = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={},
            compose_naming=self._naming(prefix="acme"),
        )
        result = expand_env_string(
            "cost $$ and ${@service:db}",
            resolver,
            field_path="services.x.command[]",
        )
        self.assertEqual(result, "cost $ and acme-db")

    def test_compose_map_expands_environment_service_refs(self):
        resolver = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={},
            compose_naming=self._naming(prefix="acme"),
        )
        expanded = expand_env_in_compose_service_map(
            {
                "worker": {
                    "image": "busybox",
                    "environment": {
                        "DB_HOST": "${@service:db}",
                        "ODOO_URL": "http://${@service:odoo}:8069",
                    },
                    "command": ["echo", "${@service:db}"],
                }
            },
            resolver=resolver,
            field_prefix="services",
        )
        self.assertEqual(expanded["worker"]["environment"]["DB_HOST"], "acme-db")
        self.assertEqual(
            expanded["worker"]["environment"]["ODOO_URL"],
            "http://acme-odoo:8069",
        )
        self.assertEqual(expanded["worker"]["command"], ["echo", "acme-db"])


class RefreshManifestViewComposeExpansionTests(unittest.TestCase):
    def test_reexpands_services_after_source_materialize(self):
        from dev_project.config.transforms.env_substitution import (
            inject_service_source_paths,
        )
        from dev_project.manifest.reader import (
            load_manifest,
            refresh_manifest_view_compose_expansion,
        )
        from tests.test_manifest_v2_reader import _minimal_v2

        view = load_manifest(
            _minimal_v2(
                service_sources={
                    "autoparts_env": "https://github.com/org/autoparts-env.git 17.0",
                },
                services={
                    "armtek_test": {
                        "image": "autoparts_env:emulator",
                        "volumes": ["${@source:autoparts_env}/data:/data:Z"],
                    }
                },
            ),
            env_resolver=EnvResolver.from_sources(process_environ={}, project_dotenv={}),
        )
        self.assertEqual(
            view.services["armtek_test"]["volumes"],
            ["${@source:autoparts_env}/data:/data:Z"],
        )
        resolver = inject_service_source_paths(
            EnvResolver.from_sources(process_environ={}, project_dotenv={}),
            {"autoparts_env": "/opt/autoparts-env"},
        )
        refreshed = refresh_manifest_view_compose_expansion(view, env_resolver=resolver)
        self.assertEqual(
            refreshed.services["armtek_test"]["volumes"],
            ["/opt/autoparts-env/data:/data:Z"],
        )

    def test_load_manifest_expands_service_refs_when_naming_present(self):
        from dev_project.compose.service_names import resolve_compose_naming
        from dev_project.manifest.reader import load_manifest
        from tests.test_manifest_v2_reader import _minimal_v2

        naming = resolve_compose_naming(
            compose_prefix_raw="acme",
            legacy_postgres_service_name="db",
        )
        view = load_manifest(
            _minimal_v2(
                services={
                    "worker": {
                        "image": "busybox",
                        "environment": {"DB_HOST": "${@service:db}"},
                    }
                },
            ),
            env_resolver=EnvResolver.from_sources(
                process_environ={},
                project_dotenv={},
                compose_naming=naming,
            ),
        )
        self.assertEqual(view.services["worker"]["environment"]["DB_HOST"], "acme-db")


class ExpandEnvInJsonTests(unittest.TestCase):
    def test_expands_whitelist_fields_only(self):
        resolver = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={
                "PLATFORM": "/tmp/odoo",
                "DEP": "/tmp/oca/web",
            },
        )
        raw = {
            "odoo_version": "17.${ODOO_VER}",
            "odoo_git_link": "file://${PLATFORM}",
            "dependencies": [
                "file://${DEP}",
                "https://github.com/OCA/sale.git 17.0",
            ],
            "requirements_txt": ["${PIP_EXTRA}"],
        }
        expanded = expand_env_in_json(
            raw,
            resolver=resolver,
            allowed_fields=ODPM_JSON_ENV_EXPAND_FIELDS,
        )
        self.assertEqual(expanded["odoo_version"], "17.${ODOO_VER}")
        self.assertEqual(expanded["odoo_git_link"], "file:///tmp/odoo")
        self.assertEqual(
            expanded["dependencies"],
            ["file:///tmp/oca/web", "https://github.com/OCA/sale.git 17.0"],
        )
        self.assertEqual(expanded["requirements_txt"], ["${PIP_EXTRA}"])

    def test_non_dict_input_returned_unchanged(self):
        resolver = EnvResolver.from_sources(process_environ={}, project_dotenv={})
        self.assertIsNone(
            expand_env_in_json(None, resolver=resolver, allowed_fields=frozenset())
        )


class ExpandComposeServiceMapTests(unittest.TestCase):
    def test_expands_services_and_patches_string_fields(self):
        resolver = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={"DATA_DIR": "/opt/autoparts/data"},
        )
        services = {
            "armtek": {
                "image": "autoparts_env:emulator",
                "user": "root",
                "volumes": ["${DATA_DIR}:/data:Z"],
                "environment": {"HOST": "${DATA_DIR}"},
                "command": ["sh", "-c", "echo ${DATA_DIR}"],
            }
        }
        expanded = expand_env_in_compose_service_map(
            services,
            resolver=resolver,
            field_prefix="services",
        )
        self.assertEqual(
            expanded,
            {
                "armtek": {
                    "image": "autoparts_env:emulator",
                    "user": "root",
                    "volumes": ["/opt/autoparts/data:/data:Z"],
                    "environment": {"HOST": "/opt/autoparts/data"},
                    "command": ["sh", "-c", "echo /opt/autoparts/data"],
                }
            },
        )

    def test_merged_subprocess_environ_prefers_process_over_dotenv(self):
        resolver = EnvResolver.from_sources(
            process_environ={"BUILD_DIR": "/from-process"},
            project_dotenv={"BUILD_DIR": "/from-dotenv", "ONLY_DOTENV": "yes"},
        )
        merged = merged_subprocess_environ(resolver)
        self.assertEqual(merged["BUILD_DIR"], "/from-process")
        self.assertEqual(merged["ONLY_DOTENV"], "yes")

    def test_expands_networks_list_in_compose_services(self):
        resolver = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={"PROXY_NETWORK": "proxy"},
        )
        services = {
            "metrics": {
                "image": "prom/prometheus",
                "networks": ["${PROXY_NETWORK}"],
            }
        }
        expanded = expand_env_in_compose_service_map(
            services,
            resolver=resolver,
            field_prefix="services",
        )
        self.assertEqual(expanded["metrics"]["networks"], ["proxy"])

    def test_strips_source_field_from_compose_spec(self):
        resolver = EnvResolver.from_sources(process_environ={}, project_dotenv={})
        services = {
            "armtek": {
                "source": "autoparts_env",
                "image": "autoparts_env:emulator",
            }
        }
        expanded = expand_env_in_compose_service_map(
            services,
            resolver=resolver,
            field_prefix="services",
        )
        self.assertNotIn("source", expanded["armtek"])

    def test_expands_hostname_and_healthcheck_strings(self):
        resolver = EnvResolver.from_sources(
            process_environ={"HC_HOST": "127.0.0.1"},
            project_dotenv={"SIDECAR_HOST": "minio-local"},
        )
        services = {
            "minio": {
                "image": "minio/minio:latest",
                "hostname": "${SIDECAR_HOST}",
                "healthcheck": {
                    "test": [
                        "CMD",
                        "curl",
                        "-f",
                        "http://${HC_HOST}:9000/minio/health/live",
                    ],
                    "interval": "${HC_INTERVAL:-30s}",
                    "retries": 3,
                },
            }
        }
        expanded = expand_env_in_compose_service_map(
            services,
            resolver=resolver,
            field_prefix="services",
        )
        self.assertEqual(expanded["minio"]["hostname"], "minio-local")
        self.assertEqual(
            expanded["minio"]["healthcheck"]["test"][-1],
            "http://127.0.0.1:9000/minio/health/live",
        )
        self.assertEqual(expanded["minio"]["healthcheck"]["interval"], "30s")
        self.assertEqual(expanded["minio"]["healthcheck"]["retries"], 3)


class SecretRefExpansionTests(unittest.TestCase):
    def test_expands_dotted_secret_key(self):
        resolver = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={},
            secrets={"partner_armtek.armtek.apilogin": "login-value"},
        )
        result = expand_env_string(
            "${@secret:partner_armtek.armtek.apilogin}",
            resolver,
            field_path="services.armtek.environment.APILOGIN",
        )
        self.assertEqual(result, "login-value")

    def test_secret_coexists_with_dollar_escape(self):
        resolver = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={},
            secrets={"api.key": "secret"},
        )
        result = expand_env_string(
            "cost $$ and ${@secret:api.key}",
            resolver,
            field_path="services.x.command[]",
        )
        self.assertEqual(result, "cost $ and secret")

    def test_missing_secret_key_raises(self):
        resolver = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={},
            secrets={"other.key": "x"},
        )
        with self.assertRaises(ConfigError) as ctx:
            expand_env_string(
                "${@secret:missing.key}",
                resolver,
                field_path="services.x.environment.TOKEN",
            )
        self.assertIn("missing.key", str(ctx.exception))

    def test_empty_secrets_map_raises_file_gate_message(self):
        resolver = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={},
            secrets={},
        )
        with self.assertRaises(ConfigError) as ctx:
            expand_env_string(
                "${@secret:api.key}",
                resolver,
                field_path="services.x.environment.TOKEN",
            )
        message = str(ctx.exception)
        self.assertIn("secrets.json", message)
        self.assertIn("--secrets-file", message)

    def test_placeholder_secret_raises(self):
        resolver = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={},
            secrets={"api.key": "REPLACE_ME"},
        )
        with self.assertRaises(ConfigError) as ctx:
            expand_env_string(
                "${@secret:api.key}",
                resolver,
                field_path="services.x.environment.TOKEN",
            )
        message = str(ctx.exception).lower()
        self.assertIn("api.key", message)
        self.assertTrue(
            "placeholder" in message or "заглуш" in message,
            msg=message,
        )

    def test_allow_unresolved_secret_preserves_token(self):
        resolver = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={},
            secrets={},
        )
        result = expand_env_string(
            "${@secret:api.key}",
            resolver,
            field_path="services.x.environment.TOKEN",
            allow_unresolved_secret=True,
        )
        self.assertEqual(result, "${@secret:api.key}")

    def test_with_secrets_and_inject_preserve_secrets(self):
        base = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={},
            secrets={"api.key": "v1"},
        )
        updated = with_secrets(base, {"api.key": "v2", "other": "o"})
        self.assertEqual(updated.secrets["api.key"], "v2")
        injected = inject_service_source_paths(updated, {"autoparts_env": "/opt/src"})
        self.assertEqual(injected.secrets["api.key"], "v2")
        self.assertEqual(injected.resolve("ODPM_SOURCE_AUTOPARTS_ENV"), "/opt/src")

    def test_collect_secret_refs_in_nested_tree(self):
        refs = collect_secret_refs_in_value(
            {
                "environment": {
                    "USER": "${@secret:partner_armtek.armtek.apilogin}",
                    "PASS": "${@secret:partner_armtek.armtek.apipass}",
                },
                "command": ["echo", "$$", "${VAR}"],
            }
        )
        self.assertEqual(
            refs,
            {
                "partner_armtek.armtek.apilogin",
                "partner_armtek.armtek.apipass",
            },
        )

    def test_compose_environment_expands_secret(self):
        resolver = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={},
            secrets={"partner_armtek.armtek.apilogin": "u1"},
        )
        expanded = expand_env_in_compose_service_map(
            {
                "armtek": {
                    "image": "armtek:latest",
                    "environment": {
                        "APILOGIN": "${@secret:partner_armtek.armtek.apilogin}",
                    },
                }
            },
            resolver=resolver,
            field_prefix="services",
        )
        self.assertEqual(expanded["armtek"]["environment"]["APILOGIN"], "u1")


if __name__ == "__main__":
    unittest.main()
