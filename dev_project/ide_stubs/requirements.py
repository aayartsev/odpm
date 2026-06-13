"""Pip requirement normalization for Odoo core type stubs (IDE / Pylance)."""

from __future__ import annotations

from .. import constants


def _package_name(requirement: str) -> str:
    spec = requirement.split(";", 1)[0].strip()
    if " @ " in spec:
        spec = spec.split(" @ ", 1)[0]
    for separator in ("==", ">=", "<=", "!=", "~=", ">", "<", "["):
        if separator in spec:
            spec = spec.split(separator, 1)[0]
    return spec.strip().lower().replace("_", "-")


def is_odoo_stubs_requirement(requirement: str) -> bool:
    normalized = _package_name(requirement)
    return normalized in {
        name.replace("_", "-")
        for name in constants.ODOO_STUBS_PACKAGE_NAMES
    }


def odoo_stubs_git_branch(odoo_version: str) -> str | None:
    """Return odoo-ide/odoo-stubs git branch for *odoo_version*, or None when not needed."""
    text = str(odoo_version).strip()
    if not text:
        return None
    major_text = text.split(".", 1)[0]
    try:
        major = int(major_text)
    except ValueError:
        return None
    if major >= constants.ODOO_STUBS_MIN_ODOO_MAJOR_WITH_BUILTIN_TYPING:
        return None
    return f"{major}.0"


def odoo_stubs_pip_requirement(odoo_version: str) -> str | None:
    branch = odoo_stubs_git_branch(odoo_version)
    if not branch:
        return None
    return (
        f"odoo-stubs @ git+{constants.ODOO_STUBS_GIT_REPO}@{branch}"
    )


def normalize_odoo_stubs_requirements(
    requirements_txt: list[str],
    *,
    odoo_version: str,
    install_odoo_stubs: bool,
) -> list[str]:
    cleaned = [req.strip() for req in requirements_txt if req and req.strip()]
    cleaned = [req for req in cleaned if not is_odoo_stubs_requirement(req)]
    if not install_odoo_stubs:
        return cleaned
    pip_req = odoo_stubs_pip_requirement(odoo_version)
    if not pip_req:
        return cleaned
    return cleaned + [pip_req]
