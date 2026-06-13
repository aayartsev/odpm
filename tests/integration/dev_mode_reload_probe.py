"""Probe Odoo ``--dev=reload`` autoreload on a mounted developing-project ``.py`` file."""

from __future__ import annotations

import json
import re
import subprocess
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

AUTO_RELOAD_DISABLED_RE = re.compile(
    r"Code autoreload feature is disabled",
    re.IGNORECASE,
)
AUTO_RELOAD_WATCHER_RE = re.compile(
    r"AutoReload watcher running with (inotify|watchdog)",
    re.IGNORECASE,
)
AUTO_RELOAD_TRIGGERED_RE = re.compile(
    r"autoreload: python code updated, autoreload activated",
    re.IGNORECASE,
)
PROBE_COMMENT_PREFIX = "# odpm-autoreload-probe:"


@dataclass(frozen=True)
class AutoreloadProbeResult:
    outcome: Literal["activated", "disabled", "not_triggered"]
    probe_file: str
    detail: str
    logs_excerpt: str = ""


def repo_basename_from_developing_link(developing_link: str) -> str:
    link = (developing_link or "").strip().rstrip("/")
    if not link:
        return ""
    name = link.rsplit("/", 1)[-1]
    if name.endswith(".git"):
        name = name[:-4]
    return name


def resolve_developing_project_local_path(
    project_dir: Path,
    *,
    user_settings_path: Path | None = None,
) -> Path:
    settings_path = user_settings_path or (project_dir / "user_settings.json")
    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    developing_link = str(payload.get("developing_project") or "")
    repo_name = repo_basename_from_developing_link(developing_link)
    if not repo_name:
        raise ValueError("developing_project is not set in user_settings.json")

    compose_content = (project_dir / "docker-compose.yml").read_text(encoding="utf-8")
    for line in compose_content.splitlines():
        stripped = line.strip()
        if not stripped.startswith("- ") or ":" not in stripped:
            continue
        mount_spec = stripped[2:]
        local_path = mount_spec.split(":", 1)[0]
        docker_path = mount_spec.split(":", 1)[1]
        if repo_name in local_path and "extra-addons" in docker_path:
            path = Path(local_path)
            if path.is_dir():
                return path
    raise ValueError(
        f"Could not find compose volume mount for developing repo {repo_name!r}"
    )


def resolve_probe_python_file(
    project_dir: Path,
    *,
    user_settings_path: Path | None = None,
) -> Path:
    settings_path = user_settings_path or (project_dir / "user_settings.json")
    payload = json.loads(settings_path.read_text(encoding="utf-8"))
    developing_root = resolve_developing_project_local_path(
        project_dir, user_settings_path=settings_path
    )

    init_modules = str(payload.get("init_modules") or "").strip()
    module_names = [
        name.strip()
        for name in init_modules.split(",")
        if name.strip()
    ]
    candidates: list[Path] = []
    for module_name in module_names:
        candidates.append(developing_root / module_name / "__init__.py")
    candidates.extend(sorted(developing_root.glob("*/__init__.py")))
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    raise ValueError(f"No probe __init__.py found under {developing_root}")


def odoo_container_id(
    compose_argv: list[str], project_dir: Path, service: str = "odoo"
) -> str:
    result = subprocess.run(
        compose_argv + ["ps", "-q", service],
        cwd=project_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    container_id = (result.stdout or "").strip().splitlines()
    if result.returncode != 0 or not container_id:
        raise RuntimeError("odoo container is not running")
    return container_id[0]


def fetch_odoo_logs(
    compose_argv: list[str],
    project_dir: Path,
    *,
    tail: int = 200,
) -> str:
    result = subprocess.run(
        compose_argv
        + ["logs", "--no-color", "--tail", str(tail), "odoo"],
        cwd=project_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    return (result.stdout or result.stderr or "").strip()


def classify_autoreload_support(logs: str) -> Literal["disabled", "watcher_active", "unknown"]:
    if AUTO_RELOAD_DISABLED_RE.search(logs):
        return "disabled"
    if AUTO_RELOAD_WATCHER_RE.search(logs):
        return "watcher_active"
    return "unknown"


def append_probe_comment(probe_file: Path) -> str:
    original = probe_file.read_text(encoding="utf-8")
    marker_line = f"{PROBE_COMMENT_PREFIX}{uuid.uuid4().hex}\n"
    if marker_line.strip() in original:
        original = re.sub(
            rf"^{re.escape(PROBE_COMMENT_PREFIX)}.*\n",
            "",
            original,
            flags=re.MULTILINE,
        )
    probe_file.write_text(original + marker_line, encoding="utf-8")
    return original


def restore_probe_file(probe_file: Path, original_content: str) -> None:
    probe_file.write_text(original_content, encoding="utf-8")


def wait_for_autoreload_trigger(
    compose_argv: list[str],
    project_dir: Path,
    *,
    timeout: float = 90.0,
    poll_interval: float = 2.0,
) -> bool:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        logs = fetch_odoo_logs(compose_argv, project_dir, tail=300)
        if AUTO_RELOAD_TRIGGERED_RE.search(logs):
            return True
        time.sleep(poll_interval)
    return False


def run_autoreload_probe(
    compose_argv: list[str],
    project_dir: Path,
    probe_file: Path,
    *,
    trigger_timeout: float = 90.0,
) -> AutoreloadProbeResult:
    probe_file = probe_file.resolve()
    startup_logs = fetch_odoo_logs(compose_argv, project_dir, tail=400)
    support = classify_autoreload_support(startup_logs)

    if support == "disabled":
        return AutoreloadProbeResult(
            outcome="disabled",
            probe_file=str(probe_file),
            detail=(
                "Odoo logged that code autoreload is disabled "
                "(inotify/watchdog missing in container)"
            ),
            logs_excerpt=_extract_relevant_lines(startup_logs),
        )

    if support != "watcher_active":
        return AutoreloadProbeResult(
            outcome="not_triggered",
            probe_file=str(probe_file),
            detail="AutoReload watcher did not start and no disabled warning was found",
            logs_excerpt=_extract_relevant_lines(startup_logs),
        )

    original_content = append_probe_comment(probe_file)
    try:
        triggered = wait_for_autoreload_trigger(
            compose_argv,
            project_dir,
            timeout=trigger_timeout,
        )
    finally:
        restore_probe_file(probe_file, original_content)

    if triggered:
        logs = fetch_odoo_logs(compose_argv, project_dir, tail=120)
        return AutoreloadProbeResult(
            outcome="activated",
            probe_file=str(probe_file),
            detail="Odoo autoreload fired after saving a .py file",
            logs_excerpt=_extract_relevant_lines(logs),
        )

    logs = fetch_odoo_logs(compose_argv, project_dir, tail=200)
    return AutoreloadProbeResult(
        outcome="not_triggered",
        probe_file=str(probe_file),
        detail=(
            "Watcher was active but autoreload did not trigger after probe file save"
        ),
        logs_excerpt=_extract_relevant_lines(logs),
    )


def _extract_relevant_lines(logs: str, *, limit: int = 20) -> str:
    keywords = (
        "autoreload",
        "AutoReload",
        "Watching addons",
        "inotify",
        "watchdog",
    )
    lines = [line for line in logs.splitlines() if any(k in line for k in keywords)]
    if not lines:
        lines = logs.splitlines()[-limit:]
    return "\n".join(lines[-limit:])
