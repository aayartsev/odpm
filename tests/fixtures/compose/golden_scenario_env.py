"""Deterministic CreateProjectEnvironment for compose golden snapshots."""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.compose.compose_document import build_compose_document
from dev_project.compose.start_command import ComposeOdooService
from dev_project.debugger.constants import (
    DEBUGGER_BACKEND_DEBUGPY_LISTEN,
    DEFAULT_DEBUGGER_CONNECT_HOST,
)
from dev_project.project_env import CreateProjectEnvironment
from dev_project.project_env.types import MappedPath
from dev_project.scenario_policy import ScenarioPolicy
from dev_project.yaml import dump_document

GOLDEN_PROJECT_DIR = "/tmp/odpm-golden-fixture-project"
GOLDEN_POSTGRES_DATA = "/tmp/odpm-golden-postgres-data"
GOLDEN_MAPPED_LOCAL = "/tmp/odpm-golden-local-addons"
GOLDEN_RUNTIME_USER = "1000:1000"


def make_golden_compose_env(scenario: str) -> CreateProjectEnvironment:
    policy = ScenarioPolicy.from_scenario(scenario)
    config = MagicMock()
    config.project_dir = GOLDEN_PROJECT_DIR
    config.policy = policy
    config.odoo_image_name = "odoo-base:dev"
    config.odoo_ci_image_name = "odoo-ci:19"
    config.compose_service = ComposeOdooService(
        working_dir="/home/odoo",
        include_runtime_config=policy.mount_runtime_config_from_host(),
        include_runtime_secrets=False,
        command=[
            "python3",
            "-m",
            constants.RUN_ODOO_ENTRYPOINT,
            "--",
            "/home/odoo/odoo/odoo-bin",
        ],
    )
    config.compose_file_version = "3.8"
    config.postgres_version = "16"
    config.postgres_data_local_storage = GOLDEN_POSTGRES_DATA
    config.pd_manager = MagicMock()
    config.bootstrap = MagicMock(manifest_view=None)
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
    if policy.include_odoo_volumes:
        env.mapped_folders = [
            MappedPath(local=GOLDEN_MAPPED_LOCAL, docker="/home/odoo/extra-addons")
        ]
    else:
        env.mapped_folders = []
    return env


def render_golden_compose_yaml(scenario: str) -> str:
    """Render compose body YAML for *scenario* with fixed paths and runtime user."""
    import os

    os.makedirs(GOLDEN_PROJECT_DIR, exist_ok=True)
    env = make_golden_compose_env(scenario)
    with patch.object(
        ScenarioPolicy,
        "runtime_unix_user",
        return_value=GOLDEN_RUNTIME_USER,
    ):
        document = build_compose_document(env)
    return dump_document(document)
