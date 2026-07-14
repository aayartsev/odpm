"""Expand ${VAR} / ${VAR:-default} references in manifest JSON string fields."""

from __future__ import annotations

import os
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from ...errors import ConfigError
from ...translations import _

if TYPE_CHECKING:
    from ...host.user_env import CreateUserEnvironment

ODPM_JSON_ENV_EXPAND_FIELDS = frozenset({
    "dependencies",
    "odoo_git_link",
})

USER_SETTINGS_ENV_EXPAND_FIELDS = frozenset({
    "developing_project",
})

_ENV_REF_PATTERN = re.compile(
    r"\$\{@source:([a-z][a-z0-9_]*)\}|"
    r"\$\{([^}:]+)(?::-([^}]*))?\}|"
    r"\$\$"
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

    @classmethod
    def from_user_env(
        cls,
        user_env: CreateUserEnvironment,
        *,
        process_environ: Mapping[str, str] | None = None,
    ) -> EnvResolver:
        return cls.from_sources(
            process_environ=process_environ,
            project_dotenv=user_env.project_dotenv_dict(),
        )

    def resolve(self, name: str) -> str | None:
        """Return value if set in os.environ or project .env, else None."""
        if name in self.process_environ:
            return self.process_environ[name]
        if name in self.project_dotenv:
            return self.project_dotenv[name]
        return None


def expand_env_string(
    value: str,
    resolver: EnvResolver,
    *,
    field_path: str,
    allow_unresolved_source: bool = False,
) -> str:
    if "$" not in value:
        return value

    parts: list[str] = []
    last_end = 0

    for match in _ENV_REF_PATTERN.finditer(value):
        parts.append(value[last_end : match.start()])
        token = match.group(0)
        if token == "$$":
            parts.append("$")
        elif match.group(1) is not None:
            source_name = match.group(1)
            from ...manifest.service_sources import source_env_key

            env_key = source_env_key(source_name)
            resolved = resolver.resolve(env_key)
            if resolved is not None:
                parts.append(resolved)
            elif allow_unresolved_source:
                parts.append(token)
            else:
                raise ConfigError(
                    _(
                        "Service source {NAME} is not materialized "
                        "(required for manifest field {FIELD})"
                    ).format(NAME=source_name, FIELD=field_path)
                )
        else:
            name = match.group(2)
            default = match.group(3)
            resolved = resolver.resolve(name)
            if resolved is not None:
                parts.append(resolved)
            elif default is not None:
                parts.append(default)
            else:
                raise ConfigError(
                    _(
                        "Environment variable {VAR} is not set "
                        "(required for manifest field {FIELD})"
                    ).format(VAR=name, FIELD=field_path)
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
    allow_unresolved_source: bool = False,
) -> Any:
    if isinstance(value, str):
        return expand_env_string(
            value,
            resolver,
            field_path=field_path,
            allow_unresolved_source=allow_unresolved_source,
        )
    if isinstance(value, list):
        return [
            expand_env_string(
                item,
                resolver,
                field_path=f"{field_path}[]",
                allow_unresolved_source=allow_unresolved_source,
            )
            if isinstance(item, str)
            else item
            for item in value
        ]
    return value


_COMPOSE_SERVICE_STRING_SCALARS = frozenset({"image", "user", "restart"})
_COMPOSE_SERVICE_STRING_LISTS = frozenset({
    "ports",
    "volumes",
    "depends_on",
    "networks",
    "command",
    "entrypoint",
})


def merged_subprocess_environ(resolver: EnvResolver) -> dict[str, str]:
    """Process environ with project .env filling keys not already set."""
    merged = dict(resolver.process_environ)
    for key, value in resolver.project_dotenv.items():
        merged.setdefault(key, value)
    return merged


def _expand_compose_service_spec(
    spec: dict[str, Any],
    *,
    resolver: EnvResolver,
    field_prefix: str,
    allow_unresolved_source: bool = False,
) -> dict[str, Any]:
    result = dict(spec)
    for key in _COMPOSE_SERVICE_STRING_SCALARS:
        value = result.get(key)
        if isinstance(value, str):
            result[key] = expand_env_string(
                value,
                resolver,
                field_path=f"{field_prefix}.{key}",
                allow_unresolved_source=allow_unresolved_source,
            )
    for key in _COMPOSE_SERVICE_STRING_LISTS:
        value = result.get(key)
        if not isinstance(value, list):
            continue
        result[key] = [
            expand_env_string(
                item,
                resolver,
                field_path=f"{field_prefix}.{key}[]",
                allow_unresolved_source=allow_unresolved_source,
            )
            if isinstance(item, str)
            else item
            for item in value
        ]
    environment = result.get("environment")
    if isinstance(environment, dict):
        result["environment"] = {
            env_key: expand_env_string(
                env_value,
                resolver,
                field_path=f"{field_prefix}.environment.{env_key}",
                allow_unresolved_source=allow_unresolved_source,
            )
            if isinstance(env_value, str)
            else env_value
            for env_key, env_value in environment.items()
        }
    result.pop("source", None)
    return result


def expand_env_in_compose_service_map(
    services: dict[str, Any] | None,
    *,
    resolver: EnvResolver,
    field_prefix: str,
    allow_unresolved_source: bool = False,
) -> dict[str, Any] | None:
    """Expand ``${VAR}`` / ``${@source:name}`` in manifest v2 compose service maps."""
    if not isinstance(services, dict):
        return services
    expanded: dict[str, Any] = {}
    for name, spec in services.items():
        if not isinstance(spec, dict):
            expanded[str(name)] = spec
            continue
        expanded[str(name)] = _expand_compose_service_spec(
            dict(spec),
            resolver=resolver,
            field_prefix=f"{field_prefix}.{name}",
            allow_unresolved_source=allow_unresolved_source,
        )
    return expanded


def inject_service_source_paths(
    resolver: EnvResolver,
    source_paths: Mapping[str, str],
) -> EnvResolver:
    """Return resolver with ``ODPM_SOURCE_*`` keys set from materialized paths."""
    from ...manifest.service_sources import source_env_key

    merged_environ = dict(resolver.process_environ)
    for name, path in source_paths.items():
        merged_environ[source_env_key(name)] = str(path)
    return EnvResolver(
        process_environ=merged_environ,
        project_dotenv=resolver.project_dotenv,
    )


def expand_env_in_odoo_conf(
    odoo_conf: dict[str, Any] | None,
    *,
    resolver: EnvResolver,
) -> dict[str, Any] | None:
    """Expand ``${VAR}`` in manifest ``odoo_conf`` string option values."""
    if not isinstance(odoo_conf, dict):
        return odoo_conf
    expanded: dict[str, Any] = {}
    for section_name, section_data in odoo_conf.items():
        if not isinstance(section_data, dict):
            expanded[str(section_name)] = section_data
            continue
        expanded[str(section_name)] = {
            str(key): expand_env_string(
                value,
                resolver,
                field_path=f"odoo_conf.{section_name}.{key}",
            )
            if isinstance(value, str)
            else value
            for key, value in section_data.items()
        }
    return expanded


def expand_env_in_service_sources(
    service_sources: dict[str, str] | None,
    *,
    resolver: EnvResolver,
) -> dict[str, str] | None:
    """Expand ``${VAR}`` in manifest ``service_sources`` git link values."""
    if not isinstance(service_sources, dict):
        return service_sources
    expanded: dict[str, str] = {}
    for name, link in service_sources.items():
        expanded[str(name)] = expand_env_string(
            str(link),
            resolver,
            field_path=f"service_sources.{name}",
        )
    return expanded or None
