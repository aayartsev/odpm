"""Helpers for ``dev_mode`` / Odoo ``--dev`` flag handling."""

from __future__ import annotations

from . import constants
from .logging import get_module_logger

_logger = get_module_logger(__name__)


def _package_name(requirement: str) -> str:
    spec = requirement.split(";", 1)[0].strip()
    for separator in ("==", ">=", "<=", "!=", "~=", ">", "<", "["):
        if separator in spec:
            spec = spec.split(separator, 1)[0]
    return spec.strip().lower()


def is_autoreload_requirement(requirement: str) -> bool:
    return _package_name(requirement) in constants.ODOO_AUTORELOAD_PACKAGE_NAMES


def dev_mode_disabled(value: object) -> bool:
    """Return True when compose must not pass ``--dev``."""
    if value is False or value is None:
        return True
    if isinstance(value, str) and not value.strip():
        return True
    return False


def effective_dev_mode(dev_mode: object, *, apply_dev_mode: bool) -> object:
    """Return dev_mode for compose/venv, or False when disabled or scenario forbids it."""
    if not apply_dev_mode or dev_mode_disabled(dev_mode):
        return False
    return dev_mode


def dev_mode_includes_xml(value: object) -> bool:
    """True when Odoo will enable QWeb-from-XML dev behaviour (may affect HTTP)."""
    if dev_mode_disabled(value):
        return False
    text = str(value).strip().lower()
    if text == constants.ODOO_DEV_MODE_ALL:
        return True
    parts = {part.strip().lower() for part in text.split(",") if part.strip()}
    return "xml" in parts


def dev_mode_includes_reload(value: object) -> bool:
    """True when Odoo will attempt code autoreload (--dev reload or all)."""
    if dev_mode_disabled(value):
        return False
    text = str(value).strip().lower()
    if text == constants.ODOO_DEV_MODE_ALL:
        return True
    parts = {part.strip().lower() for part in text.split(",") if part.strip()}
    return "reload" in parts


def merge_autoreload_requirements(
    requirements_txt: list[str],
    dev_mode: object,
) -> list[str]:
    """Add inotify for Odoo autoreload when ``dev_mode`` includes ``reload``."""
    cleaned = [
        req
        for req in requirements_txt
        if req and req.strip() and not is_autoreload_requirement(req)
    ]
    if not dev_mode_includes_reload(dev_mode):
        return cleaned
    _logger.info(
        "dev_mode includes reload; adding %s for Odoo code autoreload",
        constants.ODOO_AUTORELOAD_INOTIFY_REQUIREMENT,
    )
    return cleaned + [constants.ODOO_AUTORELOAD_INOTIFY_REQUIREMENT]


def iter_dev_mode_compose_cases() -> list[tuple[str, object, str | None]]:
    """
    (case_id, user_settings dev_mode value, expected ``--dev`` argv or None).

    Covers every documented Odoo feature, ``all``, representative combos, and off states.
    """
    cases: list[tuple[str, object, str | None]] = [
        ("disabled_false", False, None),
        ("disabled_empty", "", None),
        ("disabled_none", None, None),
    ]
    for feature in constants.ODOO_DEV_MODE_FEATURES:
        cases.append((f"single_{feature}", feature, feature))
    cases.extend(
        [
            ("all", constants.ODOO_DEV_MODE_ALL, constants.ODOO_DEV_MODE_ALL),
            ("combo_reload_qweb", "reload,qweb", "reload,qweb"),
            (
                "combo_no_xml",
                "reload,qweb,werkzeug,access",
                "reload,qweb,werkzeug,access",
            ),
            (
                "combo_with_xml",
                "reload,qweb,werkzeug,xml",
                "reload,qweb,werkzeug,xml",
            ),
            (
                "combo_all_features_explicit",
                "reload,qweb,werkzeug,xml,access",
                "reload,qweb,werkzeug,xml,access",
            ),
        ]
    )
    return cases
