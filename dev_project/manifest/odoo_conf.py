"""Manifest ``odoo_conf`` block → runtime odoo config merge helpers."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .reader import ManifestView


def odoo_conf_from_manifest(view: ManifestView | None) -> dict[str, dict[str, str]] | None:
    """Return effective manifest ``odoo_conf`` sections or None when absent."""
    if view is None or view.odoo_conf is None:
        return None
    return _normalize_odoo_conf_sections(view.odoo_conf)


def odoo_conf_from_raw_manifest(raw: dict[str, Any]) -> dict[str, dict[str, str]] | None:
    """Extract ``odoo_conf`` from manifest JSON before env expansion."""
    odoo_conf = raw.get("odoo_conf")
    if not isinstance(odoo_conf, dict):
        return None
    return _normalize_odoo_conf_sections(odoo_conf)


def _normalize_odoo_conf_sections(
    odoo_conf: dict[str, Any],
) -> dict[str, dict[str, str]] | None:
    normalized: dict[str, dict[str, str]] = {}
    for section_name, section_data in odoo_conf.items():
        if not isinstance(section_data, dict):
            continue
        section_values = {
            str(key): str(value)
            for key, value in section_data.items()
            if value is not None
        }
        if section_values:
            normalized[str(section_name)] = section_values
    return normalized or None


def merge_odoo_conf_sections(
    base: dict[str, dict[str, str]],
    overrides: dict[str, dict[str, str]] | None,
) -> dict[str, dict[str, str]]:
    """Merge manifest overrides on top of disk-backed odoo.conf sections."""
    if not overrides:
        return {section: dict(values) for section, values in base.items()}

    merged = {section: dict(values) for section, values in base.items()}
    for section_name, section_values in overrides.items():
        section = merged.setdefault(section_name, {})
        section.update(section_values)
    return merged
