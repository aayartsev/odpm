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
from .scenario_overrides import resolve_effective_manifest_slice, validate_scenario_manifest
from .secrets_policy import collect_secrets_requirement_issues
from .schema import validate_manifest_v1, validate_manifest_v2

if TYPE_CHECKING:
    from ..host.cli.args import OdpmCliArgs
    from ..host.context import HostProjectContext
    from ..host.ports import BootstrapHandle, PipelinePorts

_logger = get_module_logger(__name__)


def run_manifest_command(cli_args: OdpmCliArgs, ports: PipelinePorts) -> int:
    bootstrap = ports.bootstrap
    host_ctx = ports.plan.host_ctx
    subcommand = cli_args.manifest_subcommand
    if subcommand == "migrate":
        return _run_manifest_migrate(cli_args, bootstrap, host_ctx)
    if subcommand == "validate":
        return _run_manifest_validate(bootstrap, host_ctx)
    raise ConfigError(
        _('manifest subcommand required: use "odpm manifest migrate" or '
          '"odpm manifest validate".')
    )


def _read_manifest_json(bootstrap: BootstrapHandle) -> tuple[str, dict]:
    manifest_path = bootstrap.repo_odpm_json
    if not isinstance(manifest_path, str) or not os.path.isfile(manifest_path):
        raise ConfigError(
            _("Manifest file not found at {PATH}.").format(PATH=manifest_path)
        )
    with open(manifest_path, encoding="utf-8") as handle:
        raw = json.load(handle)
    if not isinstance(raw, dict):
        raise ConfigError(_("Manifest root must be a JSON object."))
    return manifest_path, raw


def _run_manifest_validate(
    bootstrap: BootstrapHandle, host_ctx: HostProjectContext
) -> int:
    manifest_path, raw = _read_manifest_json(bootstrap)
    assert_manager_supports_manifest(raw)
    info = parse_manifest_version_info(raw)
    if info.manifest_schema == constants.MANIFEST_SCHEMA_V2:
        validate_manifest_v2(raw)
        schema_label = "v2"
        network_logical = getattr(host_ctx.user_env, "compose_network_logical", None)
        if not isinstance(network_logical, str) or not network_logical:
            network_logical = None
        validate_scenario_manifest(
            raw,
            compose_network_logical=network_logical,
        )
    else:
        validate_manifest_v1(raw)
        schema_label = "v1"
        network_logical = getattr(host_ctx.user_env, "compose_network_logical", None)
        if not isinstance(network_logical, str) or not network_logical:
            network_logical = None
        validate_scenario_manifest(
            raw,
            compose_network_logical=network_logical,
        )
        validate_manifest_odoo_conf(
            raw.get("odoo_conf") if isinstance(raw.get("odoo_conf"), dict) else None,
            scenario=constants.DEFAULT_ODPM_SCENARIO,
        )
    scenario = getattr(host_ctx.user_env, "odpm_scenario", None) or constants.DEFAULT_ODPM_SCENARIO
    secrets_spec = None
    if info.manifest_schema == constants.MANIFEST_SCHEMA_V2:
        effective = resolve_effective_manifest_slice(raw, str(scenario))
        secrets_spec = effective.secrets
    for issue in collect_secrets_requirement_issues(
        host_ctx.project_dir,
        secrets_spec,
        mount_secrets_from_host=host_ctx.policy.mount_runtime_secrets_from_host(),
        scenario=str(scenario),
    ):
        _logger.warning(issue)
    _logger.info(
        _("Manifest at {PATH} is valid ({SCHEMA} JSON Schema).").format(
            PATH=manifest_path,
            SCHEMA=schema_label,
        )
    )
    return 0


def _run_manifest_migrate(
    cli_args: OdpmCliArgs,
    bootstrap: BootstrapHandle,
    host_ctx: HostProjectContext,
) -> int:
    manifest_path, raw = _read_manifest_json(bootstrap)

    user_settings = bootstrap.raw_user_settings
    deps_lock = load_deps_lock(deps_lock_path(host_ctx.project_dir))
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
