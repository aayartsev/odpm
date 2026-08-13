"""Tests for compose service fragment collection, materialization, and injection."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.compose.fragments import (
    collect_compose_services,
    compose_fragments_dir,
    compose_fragments_need_materialize,
    compose_fragments_snapshot_path,
    ensure_compose_fragments_gitignore,
    materialize_compose_fragments,
    render_compose_services_block,
)
from dev_project.compose.start_command import ComposeOdooService
from dev_project.extensions.context import ExtensionHostContext
from dev_project.extensions.registry import (
    register_compose_fragment,
    reset_extension_registry_state,
)
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.host.context import HostProjectContext
from dev_project.manifest.reader import ManifestView
from dev_project.prepare.steps_compose import evaluate_compose_fragments, exec_compose_fragments
from dev_project.host.ports import ports_from_config
from dev_project.prepare.types import PrepareContext
from dev_project.project_env import CreateProjectEnvironment
from dev_project.compose.generator import ComposeGenerator
from dev_project.project_env.types import MappedPath
from dev_project.debugger.constants import DEBUGGER_BACKEND_DEBUGPY_LISTEN, DEFAULT_DEBUGGER_CONNECT_HOST
from dev_project.scenario_policy import ScenarioPolicy


class _MailpitFragment:
    name = "mailpit-plugin"

    def compose_services(self, ctx: ExtensionHostContext) -> dict:
        return {"mailpit-plugin": {"image": "plugin/mailpit:latest"}}


class ComposeFragmentsRenderTests(unittest.TestCase):
    def test_render_empty_services_returns_empty_string(self):
        self.assertEqual(render_compose_services_block({}), "")

    def test_render_service_block(self):
        block = render_compose_services_block(
            {"mailpit": {"image": "axllent/mailpit", "ports": ["8025:8025"]}}
        )
        self.assertIn("  mailpit:", block)
        self.assertIn("    image: axllent/mailpit", block)
        self.assertIn('    ports:', block)
        self.assertIn('      - 8025:8025', block)

    def test_render_service_with_user_and_tty(self):
        block = render_compose_services_block(
            {
                "sidecar": {
                    "image": "busybox:latest",
                    "user": "root",
                    "tty": True,
                }
            }
        )
        self.assertIn("    user: root", block)
        self.assertIn("    tty: true", block)

    def test_render_service_with_hostname_and_healthcheck(self):
        block = render_compose_services_block(
            {
                "minio": {
                    "image": "minio/minio:latest",
                    "hostname": "minio",
                    "healthcheck": {
                        "test": ["CMD", "curl", "-f", "http://localhost:9000/minio/health/live"],
                        "interval": "30s",
                        "retries": 3,
                    },
                }
            }
        )
        self.assertIn("    hostname: minio", block)
        self.assertIn("    healthcheck:", block)
        self.assertIn("      interval: 30s", block)
        self.assertIn("      retries: 3", block)

    def test_render_service_with_privileged_and_pid(self):
        block = render_compose_services_block(
            {
                "sysbox": {
                    "image": "example/sys:latest",
                    "privileged": True,
                    "pid": "host",
                }
            }
        )
        self.assertIn("    privileged: true", block)
        self.assertIn("    pid: host", block)


class ComposeFragmentsCollectTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_extension_registry_state()

    def tearDown(self) -> None:
        reset_extension_registry_state()

    def test_collect_merges_manifest_and_plugins(self):
        register_compose_fragment("mailpit-plugin", _MailpitFragment())
        ext = ExtensionHostContext(
            host=MagicMock(),
            repo_odpm_json="/tmp/odpm.json",
            manifest_services={"mailpit": {"image": "axllent/mailpit"}},
        )
        services = collect_compose_services(ext)
        self.assertEqual(
            services["mailpit"],
            {"image": "axllent/mailpit"},
        )
        self.assertEqual(
            services["mailpit-plugin"],
            {"image": "plugin/mailpit:latest"},
        )


class ComposeFragmentsMaterializeTests(unittest.TestCase):
    def test_materialize_writes_snapshot_and_service_yaml(self):
        with tempfile.TemporaryDirectory() as project_dir:
            services = {"mailpit": {"image": "axllent/mailpit"}}
            materialize_compose_fragments(project_dir, services)
            fragments_dir = compose_fragments_dir(project_dir)
            self.assertTrue(os.path.isfile(os.path.join(fragments_dir, "mailpit.yml")))
            snapshot = Path(compose_fragments_snapshot_path(project_dir)).read_text(
                encoding="utf-8"
            )
            payload = json.loads(snapshot)
            self.assertEqual(payload["odpm_scenario"], constants.DEVELOPER_SCENARIO)
            self.assertEqual(payload["services"], services)
            gitignore = Path(fragments_dir, ".gitignore").read_text(encoding="utf-8")
            self.assertIn("*", gitignore)

    def test_need_materialize_skips_empty_services_without_artifacts(self):
        with tempfile.TemporaryDirectory() as project_dir:
            self.assertFalse(compose_fragments_need_materialize(project_dir, {}))

    def test_need_materialize_detects_stale_snapshot(self):
        with tempfile.TemporaryDirectory() as project_dir:
            services = {"mailpit": {"image": "axllent/mailpit"}}
            self.assertTrue(
                compose_fragments_need_materialize(project_dir, services)
            )
            materialize_compose_fragments(project_dir, services)
            self.assertFalse(
                compose_fragments_need_materialize(project_dir, services)
            )
            self.assertTrue(
                compose_fragments_need_materialize(
                    project_dir,
                    {"mailpit": {"image": "other:latest"}},
                )
            )

    def test_ensure_gitignore_is_idempotent(self):
        with tempfile.TemporaryDirectory() as project_dir:
            ensure_compose_fragments_gitignore(project_dir)
            first = Path(compose_fragments_dir(project_dir), ".gitignore").read_text(
                encoding="utf-8"
            )
            ensure_compose_fragments_gitignore(project_dir)
            second = Path(compose_fragments_dir(project_dir), ".gitignore").read_text(
                encoding="utf-8"
            )
            self.assertEqual(first, second)


class ComposeFragmentsGeneratorTests(unittest.TestCase):
    def _program_dir(self) -> str:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _copy_compose_template(self, project_dir: str) -> None:
        template_dest = os.path.join(
            project_dir,
            constants.PROJECT_DOCKER_COMPOSE_TEMPLATE_FILE_RELATIVE_PATH,
        )
        os.makedirs(os.path.dirname(template_dest), exist_ok=True)
        shutil.copy(
            os.path.join(
                self._program_dir(), "dev_project", "templates", "docker-compose.yml"
            ),
            template_dest,
        )

    def test_generator_injects_manifest_service_fragment(self):
        with tempfile.TemporaryDirectory() as project_dir:
            self._copy_compose_template(project_dir)
            policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
            config = MagicMock()
            config.project_dir = project_dir
            config.policy = policy
            config.odoo_image_name = "odoo-base:dev"
            config.compose_service = ComposeOdooService(
                working_dir="/home/odoo",
                include_runtime_config=policy.mount_runtime_config_from_host(),
                include_runtime_secrets=False,
                command=["python3", "-m", constants.RUN_ODOO_ENTRYPOINT],
            )
            config.compose_file_version = "3.8"
            config.postgres_version = "16"
            config.postgres_data_local_storage = "/tmp/postgres-data"
            config.pd_manager = MagicMock()
            config.bootstrap = MagicMock()
            config.bootstrap.manifest_view = ManifestView(
                manifest_schema=constants.MANIFEST_SCHEMA_V2,
                requires_odpm="4.4",
                services={"mailpit": {"image": "axllent/mailpit"}},
                hooks=None,
                locks=None,
                raw_normalized={},
                source_raw={},
            )
            config.repo_odpm_json = os.path.join(project_dir, "odpm.json")
            user_env = MagicMock()
            user_env.postgres_port = 15432
            user_env.postgres_service_name = constants.DEFAULT_POSTGRES_SERVICE_NAME
            user_env.debugger_port = 5678
            user_env.debugger_backend = DEBUGGER_BACKEND_DEBUGPY_LISTEN
            user_env.debugger_connect_host = DEFAULT_DEBUGGER_CONNECT_HOST
            user_env.odoo_port = 8069
            user_env.gevent_port = 8072
            config.user_env = user_env
            env = CreateProjectEnvironment(config)
            env.mapped_folders = [
                MappedPath(local="/tmp/local-addons", docker="/home/odoo/extra-addons")
            ]
            content = ComposeGenerator(env).render_docker_compose_content()
            self.assertIn("  mailpit:", content)
            self.assertIn("    image: axllent/mailpit", content)


class ComposeFragmentsPrepareStepTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_extension_registry_state()

    def tearDown(self) -> None:
        reset_extension_registry_state()

    def _make_ctx(self, project_dir: str, *, services: dict | None) -> PrepareContext:
        config = MagicMock()
        config.project_dir = project_dir
        config.repo_odpm_json = os.path.join(project_dir, "odpm.json")
        config.bootstrap = MagicMock()
        config.bootstrap.manifest_view = (
            ManifestView(
                manifest_schema=constants.MANIFEST_SCHEMA_V2,
                requires_odpm="4.4",
                services=services,
                hooks=None,
                locks=None,
                raw_normalized={},
                source_raw={},
            )
            if services is not None
            else None
        )
        config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        host_ctx = HostProjectContext.from_config(config)
        ports = ports_from_config(config, MagicMock(), OdpmCliArgs())
        return PrepareContext(
            ports=ports,
            project_env=MagicMock(),
            templates=MagicMock(),
            compose_generator=MagicMock(),
            links=MagicMock(),
            system_checker=MagicMock(),
            args=MagicMock(),
            host_ctx=host_ctx,
        )

    def test_evaluate_update_when_fragments_stale(self):
        with tempfile.TemporaryDirectory() as project_dir:
            ctx = self._make_ctx(
                project_dir,
                services={"mailpit": {"image": "axllent/mailpit"}},
            )
            step = evaluate_compose_fragments(ctx)
            self.assertEqual(step.id, "compose.fragments")
            self.assertEqual(step.outcome, "update")

    def test_exec_materializes_fragments(self):
        with tempfile.TemporaryDirectory() as project_dir:
            ctx = self._make_ctx(
                project_dir,
                services={"mailpit": {"image": "axllent/mailpit"}},
            )
            exec_compose_fragments(ctx)
            self.assertTrue(
                os.path.isfile(
                    os.path.join(compose_fragments_dir(project_dir), "mailpit.yml")
                )
            )


class ComposeServicePatchTests(unittest.TestCase):
    def _program_dir(self) -> str:
        return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def _copy_compose_template(self, project_dir: str) -> None:
        template_dest = os.path.join(
            project_dir,
            constants.PROJECT_DOCKER_COMPOSE_TEMPLATE_FILE_RELATIVE_PATH,
        )
        os.makedirs(os.path.dirname(template_dest), exist_ok=True)
        shutil.copy(
            os.path.join(
                self._program_dir(), "dev_project", "templates", "docker-compose.yml"
            ),
            template_dest,
        )

    def test_generator_applies_manifest_service_patch_to_odoo(self):
        with tempfile.TemporaryDirectory() as project_dir:
            self._copy_compose_template(project_dir)
            policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
            config = MagicMock()
            config.project_dir = project_dir
            config.policy = policy
            config.odoo_image_name = "odoo-base:dev"
            config.compose_service = ComposeOdooService(
                working_dir="/home/odoo",
                include_runtime_config=policy.mount_runtime_config_from_host(),
                include_runtime_secrets=False,
                command=["python3", "-m", constants.RUN_ODOO_ENTRYPOINT],
            )
            config.compose_file_version = "3.8"
            config.postgres_version = "16"
            config.postgres_data_local_storage = "/tmp/postgres-data"
            config.pd_manager = MagicMock()
            config.bootstrap = MagicMock()
            config.bootstrap.manifest_view = ManifestView(
                manifest_schema=constants.MANIFEST_SCHEMA_V2,
                requires_odpm="4.4",
                services={
                    "worker": {
                        "image": "busybox:latest",
                        "command": ["sh", "-c", "sleep infinity"],
                    }
                },
                service_patches={
                    "odoo": {"environment": {"PATCH_FLAG": "1"}},
                },
                hooks=None,
                locks=None,
                raw_normalized={},
                source_raw={},
            )
            config.repo_odpm_json = os.path.join(project_dir, "odpm.json")
            user_env = MagicMock()
            user_env.postgres_port = 15432
            user_env.postgres_service_name = constants.DEFAULT_POSTGRES_SERVICE_NAME
            user_env.debugger_port = 5678
            user_env.debugger_backend = DEBUGGER_BACKEND_DEBUGPY_LISTEN
            user_env.debugger_connect_host = DEFAULT_DEBUGGER_CONNECT_HOST
            user_env.odoo_port = 8069
            user_env.gevent_port = 8072
            config.user_env = user_env
            env = CreateProjectEnvironment(config)
            env.mapped_folders = []
            content = ComposeGenerator(env).render_docker_compose_content()
            self.assertIn("PATCH_FLAG=1", content)
            self.assertIn("  worker:", content)
            self.assertIn("    command:", content)

    def test_build_plan_includes_compose_patch_step(self):
        from dataclasses import replace

        from dev_project.prepare.execute import build_prepare_plan

        with tempfile.TemporaryDirectory() as project_dir:
            ctx = ComposeFragmentsPrepareStepTests()._make_ctx(
                project_dir,
                services={"mailpit": {"image": "axllent/mailpit"}},
            )
            manifest_view = ManifestView(
                manifest_schema=constants.MANIFEST_SCHEMA_V2,
                requires_odpm="4.4",
                services={"mailpit": {"image": "axllent/mailpit"}},
                service_patches={"odoo": {"environment": {"X": "1"}}},
                hooks=None,
                locks=None,
                raw_normalized={},
                source_raw={},
            )
            ctx = replace(
                ctx,
                host_ctx=replace(ctx.host_ctx, manifest_view=manifest_view),
            )
            ctx.config.bootstrap.manifest_view = manifest_view
            plan = build_prepare_plan(ctx)
            step_ids = [step.id for step in plan.steps]
            self.assertIn("compose.patch.odoo", step_ids)
            self.assertLess(
                step_ids.index("compose.patch.odoo"),
                step_ids.index("compose.service"),
            )


class ComposeFragmentsScenarioSliceTests(unittest.TestCase):
    def test_need_materialize_detects_odpm_scenario_change(self):
        with tempfile.TemporaryDirectory() as project_dir:
            services = {"mailpit": {"image": "axllent/mailpit"}}
            materialize_compose_fragments(
                project_dir,
                services,
                odpm_scenario=constants.DEVELOPER_SCENARIO,
            )
            self.assertFalse(
                compose_fragments_need_materialize(
                    project_dir,
                    services,
                    odpm_scenario=constants.DEVELOPER_SCENARIO,
                )
            )
            self.assertTrue(
                compose_fragments_need_materialize(
                    project_dir,
                    services,
                    odpm_scenario=constants.SERVER_SCENARIO,
                )
            )

    def test_collect_compose_services_uses_effective_scenario_slice(self):
        from dev_project.extensions.context import ExtensionHostContext
        from dev_project.manifest.reader import load_manifest
        from tests.test_manifest_v2_reader import _minimal_v2

        raw = _minimal_v2(
            requires_odpm="4.6.0",
            services={"mailpit": {"image": "axllent/mailpit:base"}},
            scenarios={
                "server": {
                    "services": {
                        "mailpit": {"image": "axllent/mailpit:server"},
                    }
                }
            },
        )
        dev_view = load_manifest(raw, active_scenario=constants.DEVELOPER_SCENARIO)
        server_view = load_manifest(raw, active_scenario=constants.SERVER_SCENARIO)
        dev_ext = ExtensionHostContext(
            host=MagicMock(),
            repo_odpm_json="/tmp/odpm.json",
            manifest_services=dev_view.services,
            manifest_service_patches=dev_view.service_patches,
        )
        server_ext = ExtensionHostContext(
            host=MagicMock(),
            repo_odpm_json="/tmp/odpm.json",
            manifest_services=server_view.services,
            manifest_service_patches=server_view.service_patches,
        )
        self.assertEqual(
            collect_compose_services(dev_ext)["mailpit"]["image"],
            "axllent/mailpit:base",
        )
        self.assertEqual(
            collect_compose_services(server_ext)["mailpit"]["image"],
            "axllent/mailpit:server",
        )

    def test_collect_service_patches_uses_effective_scenario_slice(self):
        from dev_project.compose.fragments import collect_service_patches
        from dev_project.extensions.context import ExtensionHostContext
        from dev_project.manifest.reader import load_manifest
        from tests.test_manifest_v2_reader import _minimal_v2

        raw = _minimal_v2(
            requires_odpm="4.6.0",
            service_patches={"odoo": {"environment": {"BASE": "1"}}},
            scenarios={
                "ci": {
                    "service_patches": {
                        "odoo": {"environment": {"CI": "1"}},
                    }
                }
            },
        )
        dev_view = load_manifest(raw, active_scenario=constants.DEVELOPER_SCENARIO)
        ci_view = load_manifest(raw, active_scenario=constants.CI_SCENARIO)
        dev_ext = ExtensionHostContext(
            host=MagicMock(),
            repo_odpm_json="/tmp/odpm.json",
            manifest_service_patches=dev_view.service_patches,
        )
        ci_ext = ExtensionHostContext(
            host=MagicMock(),
            repo_odpm_json="/tmp/odpm.json",
            manifest_service_patches=ci_view.service_patches,
        )
        dev_env = collect_service_patches(dev_ext)["odoo"]["environment"]
        ci_env = collect_service_patches(ci_ext)["odoo"]["environment"]

        def _env_pairs(value):
            if isinstance(value, dict):
                return {f"{key}={val}" for key, val in value.items()}
            return set(value)

        self.assertEqual(_env_pairs(dev_env), {"BASE=1"})
        self.assertEqual(_env_pairs(ci_env), {"BASE=1", "CI=1"})

if __name__ == "__main__":
    unittest.main()
