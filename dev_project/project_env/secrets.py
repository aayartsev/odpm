"""Local secrets source (.odpm/secrets.json) and runtime materialization."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .. import constants
from ..errors import ConfigError
from ..logging import get_module_logger

_logger = get_module_logger(__name__)

SECRETS_SCHEMA_VERSION = 1
SECRETS_GITIGNORE_ENTRY = "secrets.json"


def secrets_source_path(project_dir: str) -> str:
    return os.path.join(project_dir, constants.ODPM_SECRETS_SOURCE_REL_PATH)


def secrets_runtime_path(project_dir: str) -> str:
    return os.path.join(project_dir, constants.ODPM_SECRETS_RUNTIME_REL_PATH)


def secrets_example_path(project_dir: str) -> str:
    return os.path.join(project_dir, constants.ODPM_SECRETS_EXAMPLE_REL_PATH)


def parse_secrets_payload(data: Any) -> dict[str, str]:
    if not isinstance(data, dict):
        raise ConfigError("secrets file must be a JSON object")
    version = data.get("schema_version")
    if version != SECRETS_SCHEMA_VERSION:
        raise ConfigError(
            f"unsupported secrets schema_version: {version!r} (expected {SECRETS_SCHEMA_VERSION})"
        )
    secrets_raw = data.get("secrets")
    if not isinstance(secrets_raw, dict):
        raise ConfigError("secrets file must contain a 'secrets' object")
    secrets: dict[str, str] = {}
    for key, value in secrets_raw.items():
        if not isinstance(key, str) or not key.strip():
            raise ConfigError("secrets keys must be non-empty strings")
        if not isinstance(value, str):
            raise ConfigError(f"secret value for {key!r} must be a string")
        secrets[key] = value
    return secrets


def validate_secrets_file(path: str) -> dict[str, str]:
    try:
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
    except OSError as exc:
        raise ConfigError(f"cannot read secrets file {path}: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise ConfigError(f"invalid JSON in secrets file {path}: {exc}") from exc
    return parse_secrets_payload(raw)


def normalize_secrets_payload(secrets: dict[str, str]) -> dict[str, Any]:
    return {
        "schema_version": SECRETS_SCHEMA_VERSION,
        "secrets": dict(sorted(secrets.items())),
    }


def format_secrets_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=4, sort_keys=True) + "\n"


def read_secrets_source(project_dir: str) -> dict[str, str] | None:
    path = secrets_source_path(project_dir)
    if not os.path.isfile(path):
        return None
    return validate_secrets_file(path)


def write_secrets_source(project_dir: str, secrets: dict[str, str]) -> str:
    path = secrets_source_path(project_dir)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    payload_text = format_secrets_json(normalize_secrets_payload(secrets))
    Path(path).write_text(payload_text, encoding="utf-8")
    os.chmod(path, 0o600)
    return path


def write_secrets_runtime(project_dir: str, secrets: dict[str, str]) -> str:
    from ..config.payload import ensure_runtime_dir_gitignore

    path = secrets_runtime_path(project_dir)
    ensure_runtime_dir_gitignore(project_dir)
    payload_text = format_secrets_json(normalize_secrets_payload(secrets))
    Path(path).write_text(payload_text, encoding="utf-8")
    os.chmod(path, 0o600)
    return path


def remove_secrets_runtime(project_dir: str) -> None:
    path = secrets_runtime_path(project_dir)
    if os.path.isfile(path):
        os.remove(path)


def materialize_secrets(project_dir: str) -> bool:
    secrets = read_secrets_source(project_dir)
    if secrets is None:
        remove_secrets_runtime(project_dir)
        return False

    ensure_secrets_gitignore(project_dir)
    runtime_path = secrets_runtime_path(project_dir)
    new_text = format_secrets_json(normalize_secrets_payload(secrets))
    if os.path.isfile(runtime_path):
        existing = Path(runtime_path).read_text(encoding="utf-8")
        if existing == new_text:
            return True

    write_secrets_runtime(project_dir, secrets)
    return True


def check_secrets_file_permissions(path: str) -> str | None:
    if not os.path.isfile(path):
        return None
    mode = os.stat(path).st_mode & 0o777
    if mode & 0o077:
        return (
            f"secrets file {path} is group- or world-accessible (mode {oct(mode)}); "
            "consider chmod 0600"
        )
    return None


def ensure_secrets_gitignore(project_dir: str) -> None:
    odpm_dir = os.path.join(project_dir, constants.PROJECT_SERVICE_DIRECTORY)
    os.makedirs(odpm_dir, exist_ok=True)
    gitignore_path = os.path.join(odpm_dir, ".gitignore")
    entry = SECRETS_GITIGNORE_ENTRY
    if not os.path.isfile(gitignore_path):
        Path(gitignore_path).write_text(f"{entry}\n", encoding="utf-8")
        return
    existing = Path(gitignore_path).read_text(encoding="utf-8")
    if entry not in existing.splitlines():
        suffix = "" if existing.endswith("\n") or not existing else "\n"
        Path(gitignore_path).write_text(f"{existing}{suffix}{entry}\n", encoding="utf-8")


def secrets_source_is_gitignored(project_dir: str) -> bool:
    if not os.path.isfile(secrets_source_path(project_dir)):
        return True
    gitignore_path = os.path.join(
        project_dir, constants.PROJECT_SERVICE_DIRECTORY, ".gitignore"
    )
    if not os.path.isfile(gitignore_path):
        return False
    return SECRETS_GITIGNORE_ENTRY in Path(gitignore_path).read_text(
        encoding="utf-8"
    ).splitlines()


def bake_secrets_enabled() -> bool:
    """True when CI image build should embed module secrets into the image."""
    value = os.environ.get(constants.ODPM_BAKE_SECRETS_ENV, "").strip().lower()
    return value in ("1", "true", "yes")


def prepare_secrets_for_ci_bake(project_dir: str) -> bool:
    """Materialize secrets for CI bake when :envvar:`ODPM_BAKE_SECRETS` is set.

    Returns True when a runtime secrets file exists after preparation.
    """
    if not bake_secrets_enabled():
        return False
    materialize_secrets(project_dir)
    return os.path.isfile(secrets_runtime_path(project_dir))


def import_secrets_from_path(project_dir: str, external_path: str) -> str:
    external = os.path.abspath(os.path.expanduser(external_path))
    if not os.path.isfile(external):
        raise ConfigError(f"secrets file not found: {external}")

    permission_warning = check_secrets_file_permissions(external)
    if permission_warning:
        _logger.warning(permission_warning)

    secrets = validate_secrets_file(external)
    destination = secrets_source_path(project_dir)
    os.makedirs(os.path.dirname(destination), exist_ok=True)

    if os.path.realpath(external) == os.path.realpath(destination):
        os.chmod(destination, 0o600)
        ensure_secrets_gitignore(project_dir)
        return destination

    write_secrets_source(project_dir, secrets)
    ensure_secrets_gitignore(project_dir)
    return destination
