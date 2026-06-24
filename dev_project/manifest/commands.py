"""Host CLI handlers for odpm manifest subcommands."""

from __future__ import annotations

import json
import os
from typing import TYPE_CHECKING

from .. import constants
from ..errors import ConfigError
from ..git.deps_lock import deps_lock_path, load_deps_lock
from ..logging import get_module_logger
from ..translations import _
from .compat import assert_manager_supports_manifest, parse_manifest_version_info
from .migrator import format_manifest_migration_diff, migrate_v1_flat_to_v2
from .odoo_conf_policy import validate_manifest_odoo_conf
from .schema import validate_manifest_v1, validate_manifest_v2

if TYPE_CHECKING:
    from ..config import Config
    from ..host.cli.args import OdpmCliArgs

_logger = get_module_logger(__name__)


def run_manifest_command(cli_args: OdpmCliArgs, config: Config) -> int:
    subcommand = cli_args.manifest_subcommand
    if subcommand == "migrate":
        return _run_manifest_migrate(cli_args, config)
    if subcommand == "validate":
        return _run_manifest_validate(config)
    raise ConfigError(
        _('manifest subcommand required: use "odpm manifest migrate" or '
          '"odpm manifest validate".')
    )


def _read_manifest_json(config: Config) -> tuple[str, dict]:
    manifest_path = config.repo_odpm_json
    if not os.path.isfile(manifest_path):
        raise ConfigError(
            _("Manifest file not found at {PATH}.").format(PATH=manifest_path)
        )
    with open(manifest_path, encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, dict):
        raise ConfigError(_("Manifest root must be a JSON object."))
    return manifest_path, raw


def _run_manifest_validate(config: Config) -> int:
    manifest_path, raw = _read_manifest_json(config)
    assert_manager_supports_manifest(raw)
    info = parse_manifest_version_info(raw)
    if info.manifest_schema == constants.MANIFEST_SCHEMA_V2:
        validate_manifest_v2(raw)
        schema_label = "v2"
    else:
        validate_manifest_v1(raw)
        schema_label = "v1"
    validate_manifest_odoo_conf(raw)
    _logger.info(
        _("Manifest at {PATH} is valid ({SCHEMA} JSON Schema).").format(
            PATH=manifest_path,
            SCHEMA=schema_label,
        )
    )
    return 0


def _run_manifest_migrate(cli_args: OdpmCliArgs, config: Config) -> int:
    manifest_path, raw = _read_manifest_json(config)

    user_settings = dict(config.bootstrap.raw_user_settings or {})
    deps_lock = load_deps_lock(deps_lock_path(config.project_dir))
    migrated = migrate_v1_flat_to_v2(
        raw,
        user_settings=user_settings,
        deps_lock=deps_lock,
    )
    diff = format_manifest_migration_diff(manifest_path, raw, migrated)

    if cli_args.manifest_migrate_write:
        with open(manifest_path, "w", encoding="utf-8") as handle:
            json.dump(migrated, handle, ensure_ascii=False, indent=4)
            handle.write("\n")
        _logger.info(
            _("Wrote manifest v2 to {PATH}.").format(PATH=manifest_path)
        )
        return 0

    if diff.strip():
        print(diff, end="", flush=True)
    else:
        _logger.info(_("No manifest changes to apply."))
    return 0
