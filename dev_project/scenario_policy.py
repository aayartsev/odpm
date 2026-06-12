"""Scenario-specific policy for compose and odpm pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from . import constants
from .debugger import (
    DEFAULT_DEBUGGER_BACKEND,
    get_backend,
    is_debugger_requirement,
    is_debugpy_requirement,
    normalize_debugger_requirements,
)
from .debugger.constants import (
    DEBUGGER_BACKEND_PYDEVD_CONNECT,
    DEFAULT_DEBUGGER_CONNECT_HOST,
)

VenvMode = Literal["fresh", "baked"]


@dataclass(frozen=True)
class ScenarioPolicy:
    scenario: str
    odoo_image_attr: str
    include_odoo_volumes: bool
    include_debugger_port: bool
    bind_postgres_localhost: bool
    include_debugpy: bool
    install_debugpy: bool
    apply_dev_mode: bool
    skip_ide_config: bool
    allow_build_image: bool
    venv_mode: VenvMode
    uses_host_identity: bool

    def __post_init__(self) -> None:
        if self.include_debugpy and not self.install_debugpy:
            raise ValueError(
                f"Scenario {self.scenario!r}: include_debugpy requires install_debugpy"
            )

    @classmethod
    def from_scenario(cls, scenario: str) -> ScenarioPolicy:
        normalized = scenario or constants.DEFAULT_ODPM_SCENARIO
        if normalized not in constants.ODPM_SCENARIO_VALUES:
            normalized = constants.DEFAULT_ODPM_SCENARIO

        if normalized == constants.CI_SCENARIO:
            return cls(
                scenario=normalized,
                odoo_image_attr="odoo_ci_image_name",
                include_odoo_volumes=False,
                include_debugger_port=False,
                bind_postgres_localhost=True,
                include_debugpy=False,
                install_debugpy=False,
                apply_dev_mode=False,
                skip_ide_config=True,
                allow_build_image=True,
                venv_mode=constants.VENV_MODE_BAKED,
                uses_host_identity=False,
            )
        if normalized == constants.SERVER_SCENARIO:
            return cls(
                scenario=normalized,
                odoo_image_attr="odoo_image_name",
                include_odoo_volumes=True,
                include_debugger_port=False,
                bind_postgres_localhost=True,
                include_debugpy=False,
                install_debugpy=False,
                apply_dev_mode=False,
                skip_ide_config=False,
                allow_build_image=False,
                venv_mode=constants.VENV_MODE_FRESH,
                uses_host_identity=True,
            )
        return cls(
            scenario=constants.DEVELOPER_SCENARIO,
            odoo_image_attr="odoo_image_name",
            include_odoo_volumes=True,
            include_debugger_port=True,
            bind_postgres_localhost=False,
            include_debugpy=True,
            install_debugpy=True,
            apply_dev_mode=True,
            skip_ide_config=False,
            allow_build_image=False,
            venv_mode=constants.VENV_MODE_FRESH,
            uses_host_identity=True,
        )

    @property
    def skip_vscode(self) -> bool:
        """Deprecated alias for :attr:`skip_ide_config` (VS Code + PyCharm configurators)."""
        return self.skip_ide_config

    def venv_is_baked(self) -> bool:
        return self.venv_mode == constants.VENV_MODE_BAKED

    def allows_venv_recreate(self) -> bool:
        """Fresh mode may rebuild venv; baked mode only validates pre-installed venv."""
        return self.venv_mode == constants.VENV_MODE_FRESH

    def is_ci(self) -> bool:
        return self.scenario == constants.CI_SCENARIO

    def is_developer(self) -> bool:
        return self.scenario == constants.DEVELOPER_SCENARIO

    def mount_runtime_config_from_host(self) -> bool:
        """Dev/server mount .odpm/runtime/config.json; CI bakes config into the image."""
        return not self.is_ci()

    def mount_runtime_secrets_from_host(self) -> bool:
        """Dev/server mount .odpm/runtime/secrets.json; CI has no host secrets file."""
        return not self.is_ci()

    def runtime_unix_user(self) -> str:
        """Unix user for compose and base image (host-aligned except CI)."""
        if self.uses_host_identity:
            return constants.HOST_USER
        return constants.CONTAINER_USER

    def runtime_unix_uid(self) -> str:
        if self.uses_host_identity:
            return str(constants.HOST_USER_UID)
        return constants.CONTAINER_USER_UID

    def runtime_unix_gid(self) -> str:
        if self.uses_host_identity:
            return str(constants.HOST_USER_GID)
        return constants.CONTAINER_USER_GID

    def runtime_unix_password(self) -> str:
        """Container login password for Dockerfile useradd (not the host password)."""
        return constants.CONTAINER_PASSWORD

    def debugpy_requirement(self, python_version: str) -> str | None:
        if not self.install_debugpy:
            return None
        return constants.DEBUGPY.get(python_version, constants.DEFAULT_DEBUGPY)

    def normalize_requirements(
        self,
        requirements_txt: list[str],
        *,
        python_version: str,
        debugger_backend: str | None = None,
    ) -> list[str]:
        backend_id = debugger_backend or DEFAULT_DEBUGGER_BACKEND
        return normalize_debugger_requirements(
            requirements_txt,
            python_version=python_version,
            debugger_backend=backend_id,
            install_debugger=self.install_debugpy,
        )

    def should_publish_debugger_port(self, debugger_backend: str | None = None) -> bool:
        if not self.include_debugger_port:
            return False
        backend_id = debugger_backend or DEFAULT_DEBUGGER_BACKEND
        return get_backend(backend_id).needs_compose_port_publish

    def build_dev_extra_ports(
        self, debugger_port_map: str, *, debugger_backend: str | None = None
    ) -> str:
        if not self.should_publish_debugger_port(debugger_backend):
            return ""
        return f"      - {debugger_port_map}\n"

    def should_add_debugger_extra_hosts(
        self, debugger_backend: str | None = None
    ) -> bool:
        if not self.include_debugger_port:
            return False
        backend_id = debugger_backend or DEFAULT_DEBUGGER_BACKEND
        return backend_id == DEBUGGER_BACKEND_PYDEVD_CONNECT

    def build_dev_extra_hosts(
        self, connect_host: str, *, debugger_backend: str | None = None
    ) -> str:
        if not self.should_add_debugger_extra_hosts(debugger_backend):
            return ""
        if connect_host.strip() != DEFAULT_DEBUGGER_CONNECT_HOST:
            return ""
        return '    extra_hosts:\n      - "host.docker.internal:host-gateway"\n'

    def build_postgres_port_map(self, port_map: str) -> str:
        if self.bind_postgres_localhost:
            return f"127.0.0.1:{port_map}"
        return port_map

    def build_odoo_volumes_block(self, mapped_volumes: str) -> str:
        if not mapped_volumes.strip():
            return ""
        return f"    volumes:{mapped_volumes}\n"
