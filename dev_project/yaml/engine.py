"""YAML engine for host compose generation (ruamel.yaml round-trip)."""

from __future__ import annotations

from io import StringIO
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap

# YAML 1.1 treats these unquoted scalars as non-strings in compose command lists.
_COMPOSE_QUOTED_STRINGS = frozenset(
    {"true", "false", "yes", "no", "on", "off", "null", "~"}
)


def _add_compose_str_representer(yaml: YAML) -> None:
    def _represent_compose_str(representer, data: str) -> Any:
        if data == "":
            return representer.represent_scalar(
                "tag:yaml.org,2002:str", "", style='"'
            )
        if data.isdigit() or data.lower() in _COMPOSE_QUOTED_STRINGS:
            return representer.represent_scalar(
                "tag:yaml.org,2002:str", data, style='"'
            )
        return representer.represent_scalar("tag:yaml.org,2002:str", data)

    yaml.representer.add_representer(str, _represent_compose_str)


def _yaml_load_instance() -> YAML:
    yaml = YAML(typ="safe")
    yaml.width = 4096
    yaml.allow_unicode = True
    _add_compose_str_representer(yaml)
    return yaml


def _yaml_dump_instance() -> YAML:
    """Round-trip dumper: nested sequences indent for Docker Compose CLI (Go yaml)."""
    yaml = YAML(typ="rt")
    yaml.default_flow_style = False
    yaml.indent(mapping=2, sequence=2, offset=2)
    yaml.width = 4096
    yaml.allow_unicode = True
    yaml.sort_base_mapping_type_on_output = False
    _add_compose_str_representer(yaml)
    return yaml


def load_document(text: str) -> dict[str, Any]:
    """Parse a YAML document into a dict (host-only)."""
    loaded = _yaml_load_instance().load(text)
    if loaded is None:
        return {}
    if not isinstance(loaded, dict):
        raise ValueError("YAML root must be a mapping")
    return dict(loaded)


def _to_plain_data(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _to_plain_data(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_to_plain_data(item) for item in value]
    return value


def _to_commented_data(value: Any) -> Any:
    if isinstance(value, dict):
        result = CommentedMap()
        for key, item in value.items():
            result[key] = _to_commented_data(item)
        return result
    if isinstance(value, list):
        return [_to_commented_data(item) for item in value]
    return value


def dump_document(document: dict[str, Any]) -> str:
    """Serialize a mapping to YAML text without a trailing document marker."""
    stream = StringIO()
    _yaml_dump_instance().dump(_to_commented_data(document), stream)
    return stream.getvalue()


def merge_services(
    base: dict[str, dict[str, Any]],
    overlay: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Merge compose service maps; ``overlay`` replaces whole services by name."""
    result = CommentedMap()
    extra_names = sorted(set(overlay) - set(base))
    for name in list(base.keys()) + extra_names:
        if name in overlay:
            result[name] = CommentedMap(_to_plain_data(overlay[name]))
        else:
            result[name] = CommentedMap(_to_plain_data(base[name]))
    return result


def _merge_environment_patch(
    base_env: Any, patch_env: dict[str, str]
) -> list[str]:
    if isinstance(base_env, list):
        merged = [str(item) for item in base_env]
        existing_keys = {
            entry.split("=", 1)[0]
            for entry in merged
            if isinstance(entry, str) and "=" in entry
        }
        for key, value in patch_env.items():
            if key not in existing_keys:
                merged.append(f"{key}={value}")
        return merged
    if isinstance(base_env, dict):
        combined = {str(k): str(v) for k, v in base_env.items()}
        combined.update({str(k): str(v) for k, v in patch_env.items()})
        return [f"{key}={value}" for key, value in combined.items()]
    return [f"{key}={value}" for key, value in patch_env.items()]


def _merge_service_patch(
    base: dict[str, Any], patch: dict[str, Any]
) -> dict[str, Any]:
    result = CommentedMap(_to_plain_data(base))
    for key, patch_value in patch.items():
        base_value = result.get(key)
        if (
            key == "environment"
            and isinstance(patch_value, dict)
            and base_value is not None
        ):
            result[key] = _merge_environment_patch(base_value, patch_value)
            continue
        if isinstance(patch_value, dict) and isinstance(base_value, dict):
            merged = dict(_to_plain_data(base_value))
            merged.update(_to_plain_data(patch_value))
            result[key] = CommentedMap(merged)
            continue
        result[key] = _to_plain_data(patch_value)
    return result


def merge_service_patch_maps(
    base: dict[str, dict[str, Any]],
    overlay: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Merge patch maps by service name; ``overlay`` keys win per ADR-009 field rules."""
    result: dict[str, dict[str, Any]] = {
        name: dict(_to_plain_data(spec)) for name, spec in base.items()
    }
    for name, patch in overlay.items():
        if name in result:
            result[name] = dict(_merge_service_patch(result[name], patch))
        else:
            result[name] = dict(_to_plain_data(patch))
    return result


def merge_services_with_patches(
    services: dict[str, dict[str, Any]],
    patches: dict[str, dict[str, Any]],
) -> dict[str, dict[str, Any]]:
    """Apply partial service patches (ADR-009); unknown service names raise ``ValueError``."""
    result = CommentedMap()
    for name, spec in services.items():
        result[name] = CommentedMap(_to_plain_data(spec))
    for name, patch in patches.items():
        if name not in result:
            raise ValueError(f"compose service patch targets unknown service: {name}")
        result[name] = CommentedMap(
            _merge_service_patch(dict(result[name]), patch)
        )
    return result
