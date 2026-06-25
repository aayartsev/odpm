"""Detect Docker Compose CLI capabilities from ``up --help`` and ``version`` output."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Callable

from . import constants

if TYPE_CHECKING:
    from .config import Config
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
        version = run_checked([*parts, "version"])
        if not compose_version_is_working(version.stdout):
            continue
        up_help = run_checked([*parts, "up", "--help"])
        return detect_docker_capabilities(command, up_help.stdout, version.stdout)
    return None


def cached_docker_capabilities(config: Config) -> DockerCapabilities | None:
    caps = getattr(config, "docker_capabilities", None)
    if isinstance(caps, DockerCapabilities):
        return caps
    runtime = getattr(config, "runtime", None)
    if runtime is not None:
        caps = getattr(runtime, "docker_capabilities", None)
        if isinstance(caps, DockerCapabilities):
            return caps
    return None


def resolve_docker_capabilities(
    config: Config,
    *,
    run_checked: Callable[..., CommandResult] | None = None,
) -> DockerCapabilities:
    cached = cached_docker_capabilities(config)
    if cached is not None:
        return cached
    if run_checked is None:
        from .subprocess_runner import run_checked as default_run_checked

        run_checked = default_run_checked
    probed = probe_docker_capabilities(
        config.docker_compose_command,
        run_checked=run_checked,
    )
    if hasattr(config, "docker_capabilities"):
        config.docker_capabilities = probed
    return probed
