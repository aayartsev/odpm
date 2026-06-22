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


def _yaml_instance() -> YAML:
    yaml = YAML(typ="safe")
    yaml.default_flow_style = False
    yaml.indent(mapping=2, sequence=4, offset=2)
    yaml.width = 4096
    yaml.allow_unicode = True
    yaml.sort_base_mapping_type_on_output = False

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
    return yaml


def load_document(text: str) -> dict[str, Any]:
    """Parse a YAML document into a dict (host-only)."""
    loaded = _yaml_instance().load(text)
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


def dump_document(document: dict[str, Any]) -> str:
    """Serialize a mapping to YAML text without a trailing document marker."""
    stream = StringIO()
    _yaml_instance().dump(_to_plain_data(document), stream)
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
            result[name] = CommentedMap(overlay[name])
        else:
            result[name] = CommentedMap(base[name])
    return result
