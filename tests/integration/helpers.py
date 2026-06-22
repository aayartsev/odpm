"""Shared helpers for docker integration tests."""

from __future__ import annotations

import subprocess
from pathlib import Path


def compose_service_logs(
    compose_argv: list[str],
    project_dir: Path,
    service: str,
    *,
    tail: int = 80,
) -> str:
    result = subprocess.run(
        compose_argv + ["logs", "--no-color", "--tail", str(tail), service],
        cwd=project_dir,
        capture_output=True,
        text=True,
    )
    return (result.stdout or result.stderr or "").strip()


def write_compose_debug_bundle(
    target_dir: Path,
    *,
    compose_argv: list[str],
    project_dir: Path,
    services: tuple[str, ...],
) -> None:
    """Persist compose logs for CI artifact upload on failure."""
    target_dir.mkdir(parents=True, exist_ok=True)
    for service in services:
        logs = compose_service_logs(compose_argv, project_dir, service)
        (target_dir / f"{service}.log").write_text(logs + "\n", encoding="utf-8")
    compose_file = project_dir / "docker-compose.yml"
    if compose_file.is_file():
        (target_dir / "docker-compose.yml").write_text(
            compose_file.read_text(encoding="utf-8"),
            encoding="utf-8",
        )
