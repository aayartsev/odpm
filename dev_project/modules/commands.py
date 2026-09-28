"""Host CLI handlers for odpm modules subcommands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..errors import ConfigError
from ..git.module_diff import (
    compute_module_diff_for_config,
    developing_repo_path,
    format_module_diff,
    git_rev_parse,
    write_last_applied,
)
from ..logging import get_module_logger
from ..translations import _

if TYPE_CHECKING:
    from ..config import Config
    from ..host.cli.args import OdpmCliArgs

_logger = get_module_logger(__name__)


def run_modules_command(cli_args: OdpmCliArgs, config: Config) -> int:
    subcommand = cli_args.modules_subcommand
    if subcommand == "diff":
        return _run_modules_diff(cli_args, config)
    if subcommand == "record-applied":
        return _run_modules_record_applied(config)
    raise ConfigError(
        _(
            'modules subcommand required: use "odpm modules diff" or '
            '"odpm modules record-applied".'
        )
    )


def _run_modules_diff(cli_args: OdpmCliArgs, config: Config) -> int:
    result = compute_module_diff_for_config(
        config,
        cli_diff_base=cli_args.modules_diff_base,
    )
    text = format_module_diff(result, cli_args.modules_diff_format)
    # Always stdout so eval "$(odpm modules diff --format shell)" stays clean.
    print(text, end="", flush=True)
    return 0


def _run_modules_record_applied(config: Config) -> int:
    project_dir = str(getattr(config, "project_dir", "") or "")
    if not project_dir:
        raise ConfigError(_("Project directory is not set."))
    repo_path = developing_repo_path(config)
    head_sha = git_rev_parse(repo_path, "HEAD")
    path = write_last_applied(project_dir, head_sha)
    _logger.info(
        _("Recorded developing SHA {SHA} in {PATH}.").format(SHA=head_sha, PATH=path)
    )
    return 0
