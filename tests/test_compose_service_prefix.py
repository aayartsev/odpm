"""Tests for apply_compose_prefix and logical compose document rewrite (4.7 B1)."""

from __future__ import annotations

import os
import unittest
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.compose.compose_document import build_compose_document
from dev_project.compose.service_names import (
    LOGICAL_DB,
    LOGICAL_ODOO,
    LOGICAL_POSTGRES_VOLUME,
    ComposeNamingContext,
    apply_compose_physical_names,
    apply_compose_prefix,
    resolve_compose_naming,
)
from dev_project.compose.start_command import ComposeOdooService
from dev_project.compose.validate import validate_compose_document
from dev_project.docker_capabilities import DockerCapabilities
from dev_project.debugger.constants import (
    DEBUGGER_BACKEND_DEBUGPY_LISTEN,
    DEFAULT_DEBUGGER_CONNECT_HOST,
)
from dev_project.manifest.reader import ManifestView
from dev_project.project_env import CreateProjectEnvironment
from dev_project.scenario_policy import ScenarioPolicy


from tests.fixtures.compose.golden_scenario_env import GOLDEN_POSTGRES_DATA, GOLDEN_PROJECT_DIR


def _prefix_ctx(prefix: str = "acme") -> ComposeNamingContext:
    return resolve_compose_naming(
        compose_prefix_raw=prefix,
        legacy_postgres_service_name=constants.DEFAULT_POSTGRES_SERVICE_NAME,
    )


class ApplyComposePrefixTests(unittest.TestCase):
    def test_rewrites_builtin_services_volumes_and_project_name(self):
        document = {
            "services": {
                LOGICAL_DB: {
                    "image": "postgres:16",
                    "volumes": [f"{LOGICAL_POSTGRES_VOLUME}:/var/lib/postgresql/data"],
                },
                LOGICAL_ODOO: {
                    "image": "odoo:dev",
                    "depends_on": [LOGICAL_DB],
                },
            },
            "volumes": {
                LOGICAL_POSTGRES_VOLUME: {"driver": "local"},
            },
        }
        ctx = _prefix_ctx()
        apply_compose_prefix(document, ctx)
        self.assertEqual(set(document["services"]), {"acme-db", "acme-odoo"})
        self.assertEqual(document["services"]["acme-odoo"]["depends_on"], ["acme-db"])
        self.assertEqual(
            document["services"]["acme-db"]["volumes"],
            ["acme-postgres-data:/var/lib/postgresql/data"],
        )
        self.assertIn("acme-postgres-data", document["volumes"])
        self.assertNotIn(LOGICAL_POSTGRES_VOLUME, document["volumes"])
        self.assertEqual(document["name"], "acme")

    def test_rewrites_manifest_sidecar_depends_on_db(self):
        document = {
            "services": {
                LOGICAL_DB: {"image": "postgres:16"},
                LOGICAL_ODOO: {"image": "odoo:dev", "depends_on": [LOGICAL_DB]},
                "mailpit": {"image": "axllent/mailpit", "depends_on": [LOGICAL_DB]},
            },
            "volumes": {LOGICAL_POSTGRES_VOLUME: {"driver": "local"}},
        }
        apply_compose_prefix(document, _prefix_ctx())
        self.assertEqual(document["services"]["mailpit"]["depends_on"], ["acme-db"])
        self.assertIn("mailpit", document["services"])

    def test_noop_without_prefix(self):
        document = {
            "services": {
                LOGICAL_DB: {"image": "postgres:16"},
                LOGICAL_ODOO: {"image": "odoo:dev", "depends_on": [LOGICAL_DB]},
            },
            "volumes": {LOGICAL_POSTGRES_VOLUME: {"driver": "local"}},
        }
        original_keys = set(document["services"])
        ctx = resolve_compose_naming(
            compose_prefix_raw=None,
            legacy_postgres_service_name=constants.DEFAULT_POSTGRES_SERVICE_NAME,
        )
        apply_compose_prefix(document, ctx)
        self.assertEqual(set(document["services"]), original_keys)
        self.assertNotIn("name", document)


class ApplyComposePhysicalNamesTests(unittest.TestCase):
    def test_legacy_postgres_service_name_without_prefix(self):
        document = {
            "services": {
                LOGICAL_DB: {"image": "postgres:16"},
                LOGICAL_ODOO: {"image": "odoo:dev", "depends_on": [LOGICAL_DB]},
                "mailpit": {"image": "axllent/mailpit", "depends_on": [LOGICAL_DB]},
            },
            "volumes": {LOGICAL_POSTGRES_VOLUME: {"driver": "local"}},
        }
        ctx = resolve_compose_naming(
            compose_prefix_raw=None,
            legacy_postgres_service_name="postgres",
        )
        apply_compose_physical_names(document, ctx)
        self.assertEqual(set(document["services"]), {"postgres", LOGICAL_ODOO, "mailpit"})
        self.assertEqual(document["services"]["odoo"]["depends_on"], ["postgres"])
        self.assertEqual(document["services"]["mailpit"]["depends_on"], ["postgres"])


def _make_compose_env(
    *,
    compose_prefix: str | None = None,
    postgres_service_name: str = constants.DEFAULT_POSTGRES_SERVICE_NAME,
    manifest_services: dict | None = None,
    compose_network_logical: str | None = None,
    compose_network_physical: str | None = None,
    compose_network_external: bool = False,
) -> CreateProjectEnvironment:
    policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
    config = MagicMock()
    config.project_dir = GOLDEN_PROJECT_DIR
    config.policy = policy
    config.odoo_image_name = "odoo-base:dev"
    config.compose_service = ComposeOdooService(
        working_dir="/home/odoo",
        include_runtime_config=policy.mount_runtime_config_from_host(),
        include_runtime_secrets=False,
        command=["python3", "-m", constants.RUN_ODOO_ENTRYPOINT, "--"],
    )
    config.compose_file_version = "3.8"
    config.postgres_version = "16"
    config.postgres_data_local_storage = GOLDEN_POSTGRES_DATA
    config.pd_manager = MagicMock()
    config.bootstrap = MagicMock()
    config.bootstrap.manifest_view = (
        ManifestView(
            manifest_schema=constants.MANIFEST_SCHEMA_V2,
            requires_odpm="4.4",
            services=manifest_services,
            hooks=None,
            locks=None,
            raw_normalized={},
            source_raw={},
        )
        if manifest_services is not None
        else None
    )
    config.repo_odpm_json = os.path.join(GOLDEN_PROJECT_DIR, "odpm.json")
    config.docker_capabilities = DockerCapabilities(
        compose_command=constants.DEFAULT_DOCKER_COMPOSE_COMMAND,
        compose_version_text="Docker Compose version v2.24.0",
        supports_no_log_prefix=True,
        supports_compose_up_yes=True,
        supports_pull_policy_never=False,
    )
    naming = resolve_compose_naming(
        compose_prefix_raw=compose_prefix,
        legacy_postgres_service_name=postgres_service_name,
    )
    user_env = MagicMock()
    user_env.postgres_port = 15432
    user_env.postgres_service_name = naming.postgres_service_name
    user_env.compose_prefix = naming.compose_prefix
    user_env.compose_project_name = naming.compose_project_name
    user_env.odoo_service_name = naming.odoo_service_name
    user_env.postgres_volume_name = naming.postgres_volume_name
    user_env.debugger_port = 5678
    user_env.debugger_backend = DEBUGGER_BACKEND_DEBUGPY_LISTEN
    user_env.debugger_connect_host = DEFAULT_DEBUGGER_CONNECT_HOST
    user_env.odoo_port = 8069
    user_env.gevent_port = 8072
    user_env.compose_network_logical = compose_network_logical
    user_env.compose_network_physical = compose_network_physical
    user_env.compose_network_external = compose_network_external
    config.user_env = user_env
    return CreateProjectEnvironment(config)


class BuildComposeDocumentPrefixTests(unittest.TestCase):
    def test_build_compose_document_applies_prefix(self):
        os.makedirs(GOLDEN_PROJECT_DIR, exist_ok=True)
        env = _make_compose_env(compose_prefix="acme")
        document = build_compose_document(env)
        validate_compose_document(document)
        self.assertEqual(set(document["services"]), {"acme-db", "acme-odoo"})
        self.assertEqual(document["services"]["acme-odoo"]["depends_on"], ["acme-db"])
        self.assertIn("acme-postgres-data", document["volumes"])
        self.assertEqual(document["name"], "acme")

    def test_build_compose_document_prefix_with_manifest_sidecar(self):
        os.makedirs(GOLDEN_PROJECT_DIR, exist_ok=True)
        env = _make_compose_env(
            compose_prefix="acme",
            manifest_services={
                "mailpit": {
                    "image": "axllent/mailpit",
                    "depends_on": [LOGICAL_DB],
                }
            },
        )
        document = build_compose_document(env)
        validate_compose_document(document)
        self.assertEqual(document["services"]["mailpit"]["depends_on"], ["acme-db"])

    def test_build_compose_document_expands_service_refs_with_prefix(self):
        from dev_project.config.transforms.env_substitution import (
            EnvResolver,
            expand_env_in_compose_service_map,
        )

        os.makedirs(GOLDEN_PROJECT_DIR, exist_ok=True)
        naming = resolve_compose_naming(
            compose_prefix_raw="acme",
            legacy_postgres_service_name=constants.DEFAULT_POSTGRES_SERVICE_NAME,
        )
        resolver = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={},
            compose_naming=naming,
        )
        services = expand_env_in_compose_service_map(
            {
                "worker": {
                    "image": "busybox",
                    "depends_on": [LOGICAL_DB],
                    "environment": {
                        "DB_HOST": "${@service:db}",
                        "ODOO_URL": "http://${@service:odoo}:8069",
                    },
                }
            },
            resolver=resolver,
            field_prefix="services",
        )
        env = _make_compose_env(compose_prefix="acme", manifest_services=services)
        document = build_compose_document(env)
        validate_compose_document(document)
        worker = document["services"]["worker"]
        self.assertEqual(worker["depends_on"], ["acme-db"])
        self.assertEqual(worker["environment"]["DB_HOST"], "acme-db")
        self.assertEqual(worker["environment"]["ODOO_URL"], "http://acme-odoo:8069")

    def test_build_compose_document_expands_service_refs_without_prefix(self):
        from dev_project.config.transforms.env_substitution import (
            EnvResolver,
            expand_env_in_compose_service_map,
        )

        os.makedirs(GOLDEN_PROJECT_DIR, exist_ok=True)
        naming = resolve_compose_naming(
            compose_prefix_raw=None,
            legacy_postgres_service_name=constants.DEFAULT_POSTGRES_SERVICE_NAME,
        )
        resolver = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={},
            compose_naming=naming,
        )
        services = expand_env_in_compose_service_map(
            {
                "worker": {
                    "image": "busybox",
                    "environment": {"DB_HOST": "${@service:db}"},
                }
            },
            resolver=resolver,
            field_prefix="services",
        )
        env = _make_compose_env(manifest_services=services)
        document = build_compose_document(env)
        self.assertEqual(
            document["services"]["worker"]["environment"]["DB_HOST"],
            "db",
        )

    def test_build_compose_document_expands_service_refs_legacy_postgres_name(self):
        from dev_project.config.transforms.env_substitution import (
            EnvResolver,
            expand_env_in_compose_service_map,
        )

        os.makedirs(GOLDEN_PROJECT_DIR, exist_ok=True)
        naming = resolve_compose_naming(
            compose_prefix_raw=None,
            legacy_postgres_service_name="pg",
        )
        resolver = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={},
            compose_naming=naming,
        )
        services = expand_env_in_compose_service_map(
            {
                "worker": {
                    "image": "busybox",
                    "depends_on": [LOGICAL_DB],
                    "environment": {"DB_HOST": "${@service:db}"},
                }
            },
            resolver=resolver,
            field_prefix="services",
        )
        env = _make_compose_env(
            postgres_service_name="pg",
            manifest_services=services,
        )
        document = build_compose_document(env)
        self.assertEqual(document["services"]["worker"]["depends_on"], ["pg"])
        self.assertEqual(document["services"]["worker"]["environment"]["DB_HOST"], "pg")

    def test_build_compose_document_without_prefix_matches_logical_names(self):
        os.makedirs(GOLDEN_PROJECT_DIR, exist_ok=True)
        env = _make_compose_env()
        document = build_compose_document(env)
        validate_compose_document(document)
        self.assertEqual(set(document["services"]), {LOGICAL_DB, LOGICAL_ODOO})
        self.assertNotIn("name", document)
        self.assertNotIn("networks", document)


if __name__ == "__main__":
    unittest.main()
