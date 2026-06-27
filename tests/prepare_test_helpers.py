"""Shared stubs for prepare execute tests with mocked project environments."""

from __future__ import annotations

from contextlib import contextmanager
from functools import wraps
from unittest.mock import patch

from dev_project.docker_capabilities import DockerCapabilities

_PREPARE_SERVICE_PATCH_TARGETS = (
    "dev_project.project_env.links.ProjectLinks.map_folders",
    "dev_project.project_env.templates.ProjectTemplates.generate_dockerfile",
    "dev_project.project_env.templates.ProjectTemplates.generate_dockerignore",
    "dev_project.project_env.templates.ProjectTemplates.generate_config_file",
    "dev_project.compose.generator.ComposeGenerator.generate_docker_compose_file",
    "dev_project.compose.validate.validate_compose_file",
    "dev_project.project_env.links.ProjectLinks.update_links",
    "dev_project.project_env.links.ProjectLinks.checkout_dependencies",
)


_STUB_DOCKER_CAPABILITIES = DockerCapabilities(
    compose_command="docker compose",
    compose_version_text="Docker Compose version v2.24.0",
    supports_no_log_prefix=True,
    supports_compose_up_yes=True,
    supports_pull_policy_never=True,
)


@contextmanager
def stub_prepare_service_executions():
    patches = [
        patch(target) for target in _PREPARE_SERVICE_PATCH_TARGETS
    ] + [
        patch(
            "dev_project.docker_capabilities.ensure_config_docker_capabilities",
            return_value=_STUB_DOCKER_CAPABILITIES,
        )
    ]
    mocks = [patcher.start() for patcher in patches]
    try:
        yield mocks[:-1]
    finally:
        for patcher in patches:
            patcher.stop()


def with_stub_prepare_service_executions(test_func):
    @wraps(test_func)
    def wrapper(*args, **kwargs):
        with stub_prepare_service_executions():
            return test_func(*args, **kwargs)

    return wrapper
