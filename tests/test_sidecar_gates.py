"""Tests for local sidecar gates (user_settings.sidecars)."""

from __future__ import annotations

import logging
import os
import unittest
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.compose.compose_document import build_compose_document
from dev_project.compose.fragments import compose_fragments_dir
from dev_project.compose.service_names import LOGICAL_DB, LOGICAL_ODOO
from dev_project.compose.sidecar_gates import (
    apply_sidecar_gates,
    collect_effective_compose_services,
    parse_sidecar_gates,
    scrub_service_deps,
)
from dev_project.compose.start_command import ComposeOdooService
from dev_project.compose.validate import validate_compose_document
from dev_project.config.state import UserSettingsState, user_settings_from_raw
from dev_project.errors import ConfigError
from dev_project.extensions.context import ExtensionHostContext
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.host.context import HostProjectContext
from dev_project.host.ports import ports_from_config
from dev_project.manifest.reader import ManifestView
from dev_project.plan.fragments_preview import build_compose_fragment_service_plan_steps
from dev_project.prepare.steps_compose import evaluate_compose_fragments, exec_compose_fragments
from dev_project.prepare.types import PrepareContext
from dev_project.project_env import CreateProjectEnvironment
from dev_project.debugger.constants import (
    DEBUGGER_BACKEND_DEBUGPY_LISTEN,
    DEFAULT_DEBUGGER_CONNECT_HOST,
)
from dev_project.scenario_policy import ScenarioPolicy

from tests.test_compose_service_prefix import GOLDEN_POSTGRES_DATA, GOLDEN_PROJECT_DIR
import tempfile


class ParseSidecarGatesTests(unittest.TestCase):
    def test_none_and_empty(self) -> None:
        self.assertEqual(parse_sidecar_gates(None), {})
        self.assertEqual(parse_sidecar_gates({}), {})

    def test_accepts_bool_map(self) -> None:
        self.assertEqual(
            parse_sidecar_gates({"mailpit": False, "redis": True}),
            {"mailpit": False, "redis": True},
        )

    def test_rejects_non_object(self) -> None:
        with self.assertRaises(ConfigError):
            parse_sidecar_gates([])

    def test_rejects_non_bool(self) -> None:
        with self.assertRaises(ConfigError):
            parse_sidecar_gates({"mailpit": "false"})
        with self.assertRaises(ConfigError):
            parse_sidecar_gates({"mailpit": 0})

    def test_rejects_built_in_services(self) -> None:
        with self.assertRaises(ConfigError):
            parse_sidecar_gates({LOGICAL_DB: False})
        with self.assertRaises(ConfigError):
            parse_sidecar_gates({LOGICAL_ODOO: True})


class ApplySidecarGatesTests(unittest.TestCase):
    def test_drop_false_keep_true_and_absent(self) -> None:
        services = {
            "mailpit": {"image": "mailpit"},
            "redis": {"image": "redis"},
            "worker": {"image": "busybox"},
        }
        kept, dropped = apply_sidecar_gates(
            services, {"mailpit": False, "redis": True}
        )
        self.assertEqual(set(kept), {"redis", "worker"})
        self.assertEqual(dropped, {"mailpit"})

    def test_warns_on_unknown_gate_key(self) -> None:
        with self.assertLogs(
            "dev_project.compose.sidecar_gates", level=logging.WARNING
        ) as captured:
            kept, dropped = apply_sidecar_gates(
                {"mailpit": {"image": "x"}}, {"ghost": True}
            )
        self.assertEqual(kept, {"mailpit": {"image": "x"}})
        self.assertEqual(dropped, set())
        self.assertTrue(any("ghost" in line for line in captured.output))

    def test_scrub_depends_on_list(self) -> None:
        services = {
            LOGICAL_ODOO: {"depends_on": [LOGICAL_DB, "mailpit"]},
            LOGICAL_DB: {},
        }
        scrub_service_deps(services, {"mailpit"})
        self.assertEqual(services[LOGICAL_ODOO]["depends_on"], [LOGICAL_DB])


class UserSettingsSidecarsLoadTests(unittest.TestCase):
    def test_round_trip(self) -> None:
        state = user_settings_from_raw(
            {"sidecars": {"mailpit": False}},
            beautify_module_list=lambda value: "" if value is None else str(value),
        )
        self.assertEqual(state.sidecars, {"mailpit": False})

    def test_absent_sidecars_defaults_empty(self) -> None:
        state = user_settings_from_raw(
            {},
            beautify_module_list=lambda value: "" if value is None else str(value),
        )
        self.assertEqual(state.sidecars, {})


def _compose_env(
    *,
    manifest_services: dict | None = None,
    service_patches: dict | None = None,
    sidecars: dict[str, bool] | None = None,
) -> CreateProjectEnvironment:
    policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
    config = MagicMock()
    config.project_dir = GOLDEN_PROJECT_DIR
    config.program_dir = GOLDEN_PROJECT_DIR
    config.config_home_dir = GOLDEN_PROJECT_DIR
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
    config.bootstrap.manifest_view = ManifestView(
        manifest_schema=constants.MANIFEST_SCHEMA_V2,
        requires_odpm="4.7.0",
        services=manifest_services or {},
        service_patches=service_patches,
        hooks=None,
        locks=None,
        raw_normalized={},
        source_raw={},
    )
    config.repo_odpm_json = os.path.join(GOLDEN_PROJECT_DIR, "odpm.json")
    config.user_settings = UserSettingsState(sidecars=dict(sidecars or {}))
    config.project_settings = MagicMock()
    config.docker_layout = MagicMock()
    config.addon_layout = MagicMock()
    config.docker_compose_command = constants.DEFAULT_DOCKER_COMPOSE_COMMAND
    config.arguments = OdpmCliArgs()
    user_env = MagicMock()
    user_env.postgres_port = 15432
    user_env.postgres_service_name = constants.DEFAULT_POSTGRES_SERVICE_NAME
    user_env.compose_prefix = None
    user_env.compose_project_name = None
    user_env.odoo_service_name = LOGICAL_ODOO
    user_env.postgres_volume_name = "postgres-data"
    user_env.debugger_port = 5678
    user_env.debugger_backend = DEBUGGER_BACKEND_DEBUGPY_LISTEN
    user_env.debugger_connect_host = DEFAULT_DEBUGGER_CONNECT_HOST
    user_env.odoo_port = 8069
    user_env.gevent_port = 8072
    user_env.compose_network_logical = None
    user_env.compose_network_physical = None
    user_env.compose_network_external = False
    user_env.odpm_scenario = constants.DEVELOPER_SCENARIO
    config.user_env = user_env
    return CreateProjectEnvironment(config)


class BuildComposeDocumentSidecarGatesTests(unittest.TestCase):
    def test_disabled_sidecar_absent_after_patch(self) -> None:
        os.makedirs(GOLDEN_PROJECT_DIR, exist_ok=True)
        env = _compose_env(
            manifest_services={"mailpit": {"image": "axllent/mailpit"}},
            service_patches={
                "mailpit": {"environment": {"X": "1"}},
                LOGICAL_ODOO: {"depends_on": [LOGICAL_DB, "mailpit"]},
            },
            sidecars={"mailpit": False},
        )
        document = build_compose_document(env)
        validate_compose_document(document)
        self.assertNotIn("mailpit", document["services"])
        self.assertEqual(
            document["services"][LOGICAL_ODOO]["depends_on"], [LOGICAL_DB]
        )


class FragmentsSidecarGatesTests(unittest.TestCase):
    def _make_ctx(
        self, project_dir: str, *, sidecars: dict[str, bool]
    ) -> PrepareContext:
        config = MagicMock()
        config.project_dir = project_dir
        config.program_dir = project_dir
        config.config_home_dir = project_dir
        config.repo_odpm_json = os.path.join(project_dir, "odpm.json")
        config.bootstrap = MagicMock()
        config.bootstrap.manifest_view = ManifestView(
            manifest_schema=constants.MANIFEST_SCHEMA_V2,
            requires_odpm="4.7.0",
            services={
                "mailpit": {"image": "axllent/mailpit"},
                "redis": {"image": "redis:7"},
            },
            hooks=None,
            locks=None,
            raw_normalized={},
            source_raw={},
        )
        config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        config.user_settings = UserSettingsState(sidecars=sidecars)
        config.project_settings = MagicMock()
        config.docker_layout = MagicMock()
        config.addon_layout = MagicMock()
        config.docker_compose_command = constants.DEFAULT_DOCKER_COMPOSE_COMMAND
        config.arguments = OdpmCliArgs()
        config.user_env = MagicMock()
        config.user_env.odpm_scenario = constants.DEVELOPER_SCENARIO
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

    def test_plan_and_materialize_skip_disabled(self) -> None:

        with tempfile.TemporaryDirectory() as project_dir:
            ctx = self._make_ctx(project_dir, sidecars={"mailpit": False})
            step_ids = [
                step.id for step in build_compose_fragment_service_plan_steps(ctx)
            ]
            self.assertNotIn("compose.fragment.mailpit", step_ids)
            self.assertIn("compose.fragment.redis", step_ids)

            step = evaluate_compose_fragments(ctx)
            self.assertEqual(step.outcome, "update")
            exec_compose_fragments(ctx)
            frag_dir = compose_fragments_dir(project_dir)
            self.assertFalse(os.path.isfile(os.path.join(frag_dir, "mailpit.yml")))
            self.assertTrue(os.path.isfile(os.path.join(frag_dir, "redis.yml")))

    def test_collect_effective(self) -> None:
        host = MagicMock()
        ext = ExtensionHostContext(
            host=host,
            repo_odpm_json="/tmp/odpm.json",
            manifest_services={"mailpit": {"image": "x"}, "redis": {"image": "y"}},
        )
        kept = collect_effective_compose_services(ext, {"mailpit": False})
        self.assertEqual(set(kept), {"redis"})


if __name__ == "__main__":
    unittest.main()
