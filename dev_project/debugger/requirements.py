"""Pip requirement normalization for debugger packages."""

from __future__ import annotations

from .backends import get_backend
from .constants import DEFAULT_DEBUGGER_BACKEND

_DEBUGGER_DISTRIBUTIONS = frozenset({"debugpy", "pydevd-pycharm"})


def _package_name(requirement: str) -> str:
    spec = requirement.split(";", 1)[0].strip()
    for separator in ("==", ">=", "<=", "!=", "~=", ">", "<", "["):
        if separator in spec:
            spec = spec.split(separator, 1)[0]
    return spec.strip().lower()


def is_debugger_requirement(requirement: str) -> bool:
    return _package_name(requirement) in _DEBUGGER_DISTRIBUTIONS


def is_debugpy_requirement(requirement: str) -> bool:
    return _package_name(requirement) == "debugpy"


def normalize_debugger_requirements(
    requirements_txt: list[str],
    *,
    python_version: str,
    debugger_backend: str,
    install_debugger: bool,
) -> list[str]:
    cleaned = [req.strip() for req in requirements_txt if req and req.strip()]
    cleaned = [req for req in cleaned if not is_debugger_requirement(req)]
    if not install_debugger:
        return cleaned
    backend = get_backend(debugger_backend or DEFAULT_DEBUGGER_BACKEND)
    pip_req = backend.pip_requirement(python_version)
    if not pip_req:
        return cleaned
    return cleaned + [pip_req]
