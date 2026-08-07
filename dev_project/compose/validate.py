"""Structural validation for generated docker-compose documents (D5 / Y3)."""

from __future__ import annotations

import os
from typing import Any

from ..errors import ConfigError
from ..translations import _
from ..yaml import load_document

_LIST_FIELDS = frozenset(
    {
        "command",
        "entrypoint",
        "ports",
        "volumes",
        "depends_on",
        "networks",
        "extra_hosts",
    }
)


def validate_compose_document(document: dict[str, Any]) -> None:
    """Validate a structured compose mapping before YAML dump or after load."""
    if not isinstance(document, dict):
        raise ConfigError(_("Generated compose document root must be a mapping"))
    services = document.get("services")
    if not isinstance(services, dict) or not services:
        raise ConfigError(_("Generated compose document must include services"))
    networks = document.get("networks")
    if networks is not None and not isinstance(networks, dict):
        raise ConfigError(_("Generated compose networks must be a mapping when present"))
    for name, spec in services.items():
        _validate_service(str(name), spec, declared_networks=networks)
    volumes = document.get("volumes")
    if volumes is not None and not isinstance(volumes, dict):
        raise ConfigError(_("Generated compose volumes must be a mapping when present"))


def validate_compose_text(text: str) -> None:
    """Parse YAML text and validate the compose document structure."""
    stripped = text.lstrip()
    if stripped.startswith("#"):
        stripped = stripped.split("\n", 1)[1].lstrip()
    document = load_document(stripped or "{}")
    validate_compose_document(document)


def validate_compose_file(path: str) -> None:
    """Validate on-disk docker-compose.yml (skips when file is missing)."""
    if not os.path.isfile(path):
        raise ConfigError(
            _("docker-compose.yml is missing at {PATH}").format(PATH=path)
        )
    try:
        text = open(path, encoding="utf-8").read()
    except OSError as exc:
        raise ConfigError(
            _("Cannot read docker-compose.yml at {PATH}: {ERROR}").format(
                PATH=path, ERROR=exc
            )
        ) from exc
    validate_compose_text(text)


def _validate_service(
    name: str,
    spec: object,
    *,
    declared_networks: dict[str, Any] | None,
) -> None:
    if not isinstance(spec, dict):
        raise ConfigError(
            _("Compose service {NAME} must be a mapping").format(NAME=name)
        )
    image = spec.get("image")
    if not isinstance(image, str) or not image.strip():
        raise ConfigError(
            _("Compose service {NAME} must define a non-empty image").format(NAME=name)
        )
    for field_name in _LIST_FIELDS:
        value = spec.get(field_name)
        if value is None:
            continue
        if not isinstance(value, list):
            raise ConfigError(
                _("Compose service {NAME}.{FIELD} must be a list").format(
                    NAME=name, FIELD=field_name
                )
            )
    environment = spec.get("environment")
    if environment is not None and not isinstance(environment, (list, dict)):
        raise ConfigError(
            _("Compose service {NAME}.environment must be a list or mapping").format(
                NAME=name
            )
        )
    if isinstance(environment, list):
        for entry in environment:
            if not isinstance(entry, str):
                raise ConfigError(
                    _(
                        "Compose service {NAME}.environment list entries must be strings"
                    ).format(NAME=name)
                )
    user = spec.get("user")
    if user is not None and (not isinstance(user, str) or not user.strip()):
        raise ConfigError(
            _("Compose service {NAME}.user must be a non-empty string").format(NAME=name)
        )
    tty = spec.get("tty")
    if tty is not None and not isinstance(tty, bool):
        raise ConfigError(
            _("Compose service {NAME}.tty must be a boolean").format(NAME=name)
        )
    hostname = spec.get("hostname")
    if hostname is not None and (not isinstance(hostname, str) or not hostname.strip()):
        raise ConfigError(
            _("Compose service {NAME}.hostname must be a non-empty string").format(
                NAME=name
            )
        )
    healthcheck = spec.get("healthcheck")
    if healthcheck is not None and not isinstance(healthcheck, dict):
        raise ConfigError(
            _("Compose service {NAME}.healthcheck must be a mapping").format(NAME=name)
        )
    if isinstance(declared_networks, dict):
        networks = spec.get("networks")
        if isinstance(networks, list):
            for entry in networks:
                if isinstance(entry, str) and entry not in declared_networks:
                    raise ConfigError(
                        _(
                            "Compose service {NAME} references undeclared network {NET}"
                        ).format(NAME=name, NET=entry)
                    )
