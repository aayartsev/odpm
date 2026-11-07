"""Detect Docker Compose CLI capabilities from ``up --help`` and ``version`` output."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from . import constants
from .errors import SystemCheckError
from .translations import _

if TYPE_CHECKING:
    from .host.ports import BootstrapHandle
    from .subprocess_runner import CommandResult


@dataclass(frozen=True)
class DockerCapabilities:
    compose_command: str
    compose_version_text: str
    supports_no_log_prefix: bool
    supports_compose_up_yes: bool
    supports_pull_policy_never: bool


_COMPOSE_VERSION_RE = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")


def _help_lists_up_yes_flag(help_text: str) -> bool:
    for line in help_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("-y,") or stripped.startswith("-y "):
            return True
        if stripped.startswith("--yes"):
            return True
    return False


def parse_compose_version(version_stdout: str) -> tuple[int, int, int] | None:
    match = _COMPOSE_VERSION_RE.search(version_stdout)
    if match is None:
        return None
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def _version_at_least(version_stdout: str, minimum: tuple[int, int]) -> bool:
    parsed = parse_compose_version(version_stdout)
    if parsed is None:
        return False
    major, minor, _patch = parsed
    return (major, minor) >= minimum


def compose_version_is_working(version_stdout: str) -> bool:
    normalized = version_stdout.lower().replace("-", " ")
    return constants.DOCKER_COMPOSE_WORKING_MESSAGE in normalized


def detect_docker_capabilities(
    compose_command: str,
    up_help_stdout: str,
    version_stdout: str,
) -> DockerCapabilities:
    supports_no_log_prefix = constants.NO_LOG_PREFIX in up_help_stdout
    supports_compose_up_yes = _help_lists_up_yes_flag(
        up_help_stdout
    ) or _version_at_least(version_stdout, (2, 23))
    supports_pull_policy_never = _version_at_least(version_stdout, (2, 2))
    return DockerCapabilities(
        compose_command=compose_command,
        compose_version_text=version_stdout.strip(),
        supports_no_log_prefix=supports_no_log_prefix,
        supports_compose_up_yes=supports_compose_up_yes,
        supports_pull_policy_never=supports_pull_policy_never,
    )


def probe_docker_capabilities(
    compose_command: str,
    *,
    run_checked: Callable[..., CommandResult],
) -> DockerCapabilities:
    parts = compose_command.split()
    up_help = run_checked([*parts, "up", "--help"])
    version = run_checked([*parts, "version"])
    return detect_docker_capabilities(
        compose_command,
        up_help.stdout,
        version.stdout,
    )


def probe_compose_command_from_candidates(
    commands: list[str],
    *,
    run_checked: Callable[..., CommandResult],
) -> DockerCapabilities | None:
    for command in commands:
        parts = command.split()
        try:
            version = run_checked([*parts, "version"])
        except FileNotFoundError:
            continue
        if not compose_version_is_working(version.stdout):
            continue
        try:
            up_help = run_checked([*parts, "up", "--help"])
        except FileNotFoundError:
            continue
        return detect_docker_capabilities(command, up_help.stdout, version.stdout)
    return None


def ensure_config_docker_capabilities(
    bootstrap: "BootstrapHandle",
    *,
    run_checked: Callable[..., "CommandResult"] | None = None,
) -> DockerCapabilities | None:
    """Probe compose CLI once and cache on the handle runtime when not already set."""
    cached = cached_docker_capabilities(bootstrap)
    if cached is not None:
        return cached
    layout_default = bootstrap.docker_layout.docker_compose_command
    compose_command = bootstrap.runtime.resolved_docker_compose_command(
        layout_default
    )
    if not isinstance(compose_command, str) or not compose_command.strip():
        return None
    if run_checked is None:
        from .subprocess_runner import run_checked as default_run_checked  # noqa: PLC0415  # optional

        run_checked = default_run_checked
    try:
        probed = probe_docker_capabilities(compose_command, run_checked=run_checked)
    except FileNotFoundError:
        return None
    bootstrap.runtime.docker_capabilities = probed
    return probed


def cached_docker_capabilities(
    bootstrap: "BootstrapHandle",
) -> DockerCapabilities | None:
    caps = bootstrap.runtime.docker_capabilities
    return caps if isinstance(caps, DockerCapabilities) else None


def resolve_docker_capabilities(
    bootstrap: "BootstrapHandle",
    *,
    run_checked: Callable[..., "CommandResult"] | None = None,
) -> DockerCapabilities:
    cached = cached_docker_capabilities(bootstrap)
    if cached is not None:
        return cached
    if run_checked is None:
        from .subprocess_runner import run_checked as default_run_checked  # noqa: PLC0415  # optional

        run_checked = default_run_checked
    try:
        probed = probe_docker_capabilities(
            bootstrap.runtime.resolved_docker_compose_command(
                bootstrap.docker_layout.docker_compose_command
            ),
            run_checked=run_checked,
        )
    except FileNotFoundError as exc:
        raise SystemCheckError(
            _("Cannot get docker-compose info, did you install it?")
        ) from exc
    bootstrap.runtime.docker_capabilities = probed
    return probed
