"""Helpers for opt-in dev_mode E2E verification against a real odpm project."""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

from dev_project.dev_mode import dev_mode_includes_xml, iter_dev_mode_compose_cases

DEV_MODE_COMPOSE_CASES = iter_dev_mode_compose_cases()


def extract_odoo_compose_command(compose_content: str) -> list[str]:
    """Return exec-form ``command`` argv for the ``odoo`` service."""
    lines = compose_content.splitlines()
    in_odoo = False
    in_command = False
    command: list[str] = []
    for line in lines:
        if re.match(r"^  odoo:\s*$", line):
            in_odoo = True
            in_command = False
            continue
        if in_odoo and re.match(r"^  [a-z0-9_-]+:\s*$", line):
            break
        if not in_odoo:
            continue
        if line.strip() == "command:":
            in_command = True
            continue
        if not in_command:
            continue
        item_match = re.match(r"^\s+-\s+(.+)\s*$", line)
        if item_match:
            token = item_match.group(1).strip()
            if (
                (token.startswith('"') and token.endswith('"'))
                or (token.startswith("'") and token.endswith("'"))
            ):
                token = token[1:-1]
            command.append(token)
            continue
        if line.strip() and not line.startswith("      "):
            break
    if not command:
        raise ValueError("odoo service command block not found in docker-compose.yml")
    return command


def dev_flag_from_compose_command(command: list[str]) -> str | None:
    if "--dev" not in command:
        return None
    index = command.index("--dev")
    if index + 1 >= len(command):
        raise ValueError("docker-compose command has --dev without a value")
    return command[index + 1]


def patch_user_settings_dev_mode(
    user_settings_path: Path, dev_mode_value: object
) -> None:
    payload = json.loads(user_settings_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{user_settings_path} must contain a JSON object")
    payload["dev_mode"] = dev_mode_value
    user_settings_path.write_text(
        json.dumps(payload, indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def expected_http_status_codes(dev_mode_value: object) -> set[int]:
    """
    Acceptable HTTP codes for ``/web/login`` after stack start.

    ``xml`` (and ``all``, which includes xml) may yield QWeb 500 on some projects;
    container must still stay up — that is validated separately.
    """
    if dev_mode_includes_xml(dev_mode_value):
        return {200, 500}
    return {200}


def container_restart_count(
    compose_argv: list[str], project_dir: Path, service: str = "odoo"
) -> int:
    result = subprocess.run(
        compose_argv + ["ps", "-q", service],
        cwd=project_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    container_id = (result.stdout or "").strip().splitlines()
    if result.returncode != 0 or not container_id:
        return -1
    inspect = subprocess.run(
        [
            "docker",
            "inspect",
            "--format",
            "{{.RestartCount}}",
            container_id[0],
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if inspect.returncode != 0:
        return -1
    try:
        return int((inspect.stdout or "0").strip())
    except ValueError:
        return -1
