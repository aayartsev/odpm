"""Compatibility checks for nested odpm.json manifests discovered in git deps."""

from __future__ import annotations

from ..translations import _
from ..dependency_resolver import NestedOdpmFragment


def _normalize_odoo_version(value: str | float | None) -> float | None:
    if value is None:
        return None
    try:
        return float(str(value).strip())
    except ValueError:
        return None


def _python_major_minor(value: str | None) -> tuple[int, int] | None:
    if not value:
        return None
    parts = str(value).strip().split(".")
    if len(parts) < 2:
        return None
    try:
        return int(parts[0]), int(parts[1])
    except ValueError:
        return None


def collect_nested_compatibility_issues(
    host_odoo_version: str | float,
    host_python_version: str,
    fragments: list[NestedOdpmFragment],
) -> list[str]:
    """Return human-readable compatibility issues for nested odpm.json fragments."""
    issues: list[str] = []
    host_odoo = _normalize_odoo_version(host_odoo_version)
    host_python = _python_major_minor(host_python_version)

    for fragment in fragments:
        if fragment.odoo_version is not None and host_odoo is not None:
            nested_odoo = _normalize_odoo_version(fragment.odoo_version)
            if nested_odoo is not None and nested_odoo != host_odoo:
                issues.append(
                    _('Nested odpm.json at {MANIFEST_PATH} declares odoo_version {NESTED_VERSION}, host project uses {HOST_VERSION}').format(
                        MANIFEST_PATH=fragment.source_path,
                        NESTED_VERSION=fragment.odoo_version,
                        HOST_VERSION=host_odoo_version,
                    )
                )

        if fragment.python_version is not None and host_python is not None:
            nested_python = _python_major_minor(fragment.python_version)
            if nested_python is not None and nested_python != host_python:
                issues.append(
                    _('Nested odpm.json at {MANIFEST_PATH} declares python_version {NESTED_VERSION}, host project uses {HOST_VERSION}').format(
                        MANIFEST_PATH=fragment.source_path,
                        NESTED_VERSION=fragment.python_version,
                        HOST_VERSION=host_python_version,
                    )
                )

    return issues
