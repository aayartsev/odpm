"""Scenario-specific policy for compose and odpm pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from . import constants

VenvMode = Literal["fresh", "baked"]


def _package_name(requirement: str) -> str:
    """Extract distribution name from a pip requirement string."""
    spec = requirement.split(";", 1)[0].strip()
    for separator in ("==", ">=", "<=", "!=", "~=", ">", "<", "["):
        if separator in spec:
            spec = spec.split(separator, 1)[0]
    return spec.strip().lower()


def is_debugpy_requirement(requirement: str) -> bool:
    return _package_name(requirement) == "debugpy"


@dataclass(frozen=True)
class ScenarioPolicy:
    scenario: str
    odoo_image_attr: str
    include_odoo_volumes: bool
    include_debugger_port: bool
    bind_postgres_localhost: bool
    include_debugpy: bool
    install_debugpy: bool
    skip_vscode: bool
    allow_build_image: bool
    venv_mode: VenvMode

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
                skip_vscode=True,
                allow_build_image=True,
                venv_mode=constants.VENV_MODE_BAKED,
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
                skip_vscode=False,
                allow_build_image=False,
                venv_mode=constants.VENV_MODE_FRESH,
            )
        return cls(
            scenario=constants.DEVELOPER_SCENARIO,
            odoo_image_attr="odoo_image_name",
            include_odoo_volumes=True,
            include_debugger_port=True,
            bind_postgres_localhost=False,
            include_debugpy=True,
            install_debugpy=True,
            skip_vscode=False,
            allow_build_image=False,
            venv_mode=constants.VENV_MODE_FRESH,
        )

    def venv_is_baked(self) -> bool:
        return self.venv_mode == constants.VENV_MODE_BAKED

    def allows_venv_recreate(self) -> bool:
        """Fresh mode may rebuild venv; baked mode only validates pre-installed venv."""
        return self.venv_mode == constants.VENV_MODE_FRESH

    def is_ci(self) -> bool:
        return self.scenario == constants.CI_SCENARIO

    def is_developer(self) -> bool:
        return self.scenario == constants.DEVELOPER_SCENARIO

    def debugpy_requirement(self, python_version: str) -> str | None:
        if not self.install_debugpy:
            return None
        return constants.DEBUGPY.get(python_version, constants.DEFAULT_DEBUGPY)

    def normalize_requirements(
        self,
        requirements_txt: list[str],
        *,
        python_version: str,
    ) -> list[str]:
        cleaned = [req.strip() for req in requirements_txt if req and req.strip()]
        cleaned = [req for req in cleaned if not is_debugpy_requirement(req)]
        debugpy = self.debugpy_requirement(python_version)
        if not debugpy:
            return cleaned
        return cleaned + [debugpy]

    def build_dev_extra_ports(self, debugger_port_map: str) -> str:
        if not self.include_debugger_port:
            return ""
        return f"      - {debugger_port_map}\n"

    def build_postgres_port_map(self, port_map: str) -> str:
        if self.bind_postgres_localhost:
            return f"127.0.0.1:{port_map}"
        return port_map

    def build_odoo_volumes_block(self, mapped_volumes: str) -> str:
        if not mapped_volumes.strip():
            return ""
        return f"    volumes:{mapped_volumes}\n"
