"""Expand ${VAR} / ${VAR:-default} references in manifest JSON string fields."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from ...errors import ConfigError

ODPM_JSON_ENV_EXPAND_FIELDS = frozenset({
    "dependencies",
    "odoo_git_link",
})

USER_SETTINGS_ENV_EXPAND_FIELDS = frozenset({
    "developing_project",
})

_ENV_REF_PATTERN = re.compile(
    r"\$\{([^}:]+)(?::-([^}]*))?\}|\$\$"
)


@dataclass(frozen=True)
class EnvResolver:
    """Resolve manifest env var names from process environ and project .env."""

    process_environ: Mapping[str, str]
    project_dotenv: Mapping[str, str]

    @classmethod
    def from_sources(
        cls,
        *,
        process_environ: Mapping[str, str] | None = None,
        project_dotenv: Mapping[str, str] | None = None,
    ) -> EnvResolver:
        environ = process_environ if process_environ is not None else os.environ
        return cls(
            process_environ={key: str(value) for key, value in environ.items()},
            project_dotenv={
                key: str(value) for key, value in (project_dotenv or {}).items()
            },
        )

    def resolve(self, name: str) -> str | None:
        """Return value if set in os.environ or project .env, else None."""
        if name in self.process_environ:
            return self.process_environ[name]
        if name in self.project_dotenv:
            return self.project_dotenv[name]
        return None


def expand_env_string(value: str, resolver: EnvResolver, *, field_path: str) -> str:
    if "$" not in value:
        return value

    parts: list[str] = []
    last_end = 0

    for match in _ENV_REF_PATTERN.finditer(value):
        parts.append(value[last_end : match.start()])
        token = match.group(0)
        if token == "$$":
            parts.append("$")
        else:
            name = match.group(1)
            default = match.group(2)
            resolved = resolver.resolve(name)
            if resolved is not None:
                parts.append(resolved)
            elif default is not None:
                parts.append(default)
            else:
                raise ConfigError(
                    f"Environment variable {name!r} is not set "
                    f"(required for manifest field {field_path})"
                )
        last_end = match.end()

    parts.append(value[last_end:])
    return "".join(parts)


def expand_env_in_json(
    data: Any,
    *,
    resolver: EnvResolver,
    allowed_fields: frozenset[str],
) -> Any:
    if not isinstance(data, dict):
        return data

    expanded = dict(data)
    for field_name in allowed_fields:
        if field_name not in expanded:
            continue
        expanded[field_name] = _expand_field_value(
            expanded[field_name],
            resolver=resolver,
            field_path=field_name,
        )
    return expanded


def _expand_field_value(
    value: Any,
    *,
    resolver: EnvResolver,
    field_path: str,
) -> Any:
    if isinstance(value, str):
        return expand_env_string(value, resolver, field_path=field_path)
    if isinstance(value, list):
        return [
            expand_env_string(item, resolver, field_path=f"{field_path}[]")
            if isinstance(item, str)
            else item
            for item in value
        ]
    return value
