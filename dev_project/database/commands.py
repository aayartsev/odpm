"""Host CLI handlers for odpm database subcommands."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING

from ..errors import ConfigError
from ..logging import get_module_logger
from ..tools.http_download import (
    assert_odoo_backup_zip,
    download_multipart_post,
    safe_host_token,
)
from ..translations import _
from .ensure_role import ensure_app_role
from .status import (
    collect_database_status,
    format_database_status_json,
    format_database_status_table,
)

if TYPE_CHECKING:
    from ..config import Config
    from ..host.cli.args import OdpmCliArgs

_logger = get_module_logger(__name__)

REMOTE_DB_MASTER_PWD_ENV = "ODPM_REMOTE_DB_MASTER_PWD"


def run_database_command(cli_args: OdpmCliArgs, config: Config) -> int:
    subcommand = cli_args.database_subcommand
    if subcommand == "status":
        return _run_database_status(cli_args, config)
    if subcommand == "ensure-role":
        return _run_database_ensure_role(config)
    if subcommand == "pull":
        return _run_database_pull(cli_args, config)
    raise ConfigError(
        _('database subcommand required: use "odpm database status", '
          '"odpm database ensure-role", or "odpm database pull".')
    )


def _run_database_status(cli_args: OdpmCliArgs, config: Config) -> int:
    report = collect_database_status(config)
    if cli_args.database_status_format == "json":
        print(format_database_status_json(report), end="", flush=True)
    else:
        _logger.info(format_database_status_table(report))
    return 0


def _run_database_ensure_role(config: Config) -> int:
    result = ensure_app_role(config)
    if result.outcome == "created":
        _logger.info(
            _("Created PostgreSQL application role {ROLE}.").format(ROLE=result.role)
        )
    else:
        _logger.info(
            _("Updated PostgreSQL application role {ROLE}.").format(ROLE=result.role)
        )
    return 0


def _backups_dir(config: Config) -> Path:
    user_env = getattr(config, "user_env", None)
    backups = ""
    if user_env is not None:
        backups = str(getattr(user_env, "backups", "") or "").strip()
    if not backups:
        raise ConfigError(
            _("BACKUP_DIR is not set; configure it in the project .env file.")
        )
    path = Path(backups).expanduser()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _run_database_pull(cli_args: OdpmCliArgs, config: Config) -> int:
    url = str(cli_args.database_pull_url or "").strip().rstrip("/")
    remote_db = str(cli_args.database_pull_remote_db or "").strip()
    if not url:
        raise ConfigError(_("--url is required for odpm database pull."))
    if not remote_db:
        raise ConfigError(_("--remote-db is required for odpm database pull."))
    master_pwd = str(os.environ.get(REMOTE_DB_MASTER_PWD_ENV) or "").strip()
    if not master_pwd:
        raise ConfigError(
            _(
                "Set {ENV} to the remote Odoo database manager master password "
                "(do not pass it on the command line)."
            ).format(ENV=REMOTE_DB_MASTER_PWD_ENV)
        )

    backups = _backups_dir(config)
    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M-%S")
    archive_name = f"{safe_host_token(url)}_{remote_db}_{stamp}.zip"
    dest = backups / archive_name
    endpoint = f"{url}/web/database/backup"
    _logger.info(
        _("Downloading remote backup for database {DB} from {URL} …").format(
            DB=remote_db,
            URL=url,
        )
    )
    download_multipart_post(
        endpoint,
        dest,
        {
            "master_pwd": master_pwd,
            "name": remote_db,
            "backup_format": "zip",
        },
    )
    try:
        assert_odoo_backup_zip(dest)
    except ConfigError:
        if dest.exists():
            dest.unlink(missing_ok=True)
        raise
    _logger.info(
        _("Remote backup saved as {NAME} under {DIR}.").format(
            NAME=archive_name,
            DIR=backups,
        )
    )
    print(archive_name, flush=True)
    return 0
