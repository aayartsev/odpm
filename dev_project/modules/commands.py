"""Host CLI handlers for odpm modules subcommands."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..errors import ConfigError
from ..git.module_diff import (
    compute_module_diff_for_handle,
    developing_repo_path,
    format_module_diff,
    git_rev_parse,
    write_last_applied,
)
from ..logging import get_module_logger
from ..translations import _

if TYPE_CHECKING:
    from ..host.cli.args import OdpmCliArgs
    from ..host.ports import BootstrapHandle, PipelinePorts

_logger = get_module_logger(__name__)


def run_modules_command(cli_args: OdpmCliArgs, ports: PipelinePorts) -> int:
    bootstrap = ports.bootstrap
    subcommand = cli_args.modules_subcommand
    if subcommand == "diff":
        return _run_modules_diff(cli_args, bootstrap)
    if subcommand == "record-applied":
        return _run_modules_record_applied(bootstrap)
    raise ConfigError(
        _(
            'modules subcommand required: use "odpm modules diff" or '
            '"odpm modules record-applied".'
        )
    )


def _run_modules_diff(cli_args: OdpmCliArgs, bootstrap: BootstrapHandle) -> int:
    result = compute_module_diff_for_handle(
        bootstrap,
        cli_diff_base=cli_args.modules_diff_base,
    )
    text = format_module_diff(result, cli_args.modules_diff_format)
    # Always stdout so eval "$(odpm modules diff --format shell)" stays clean.
    print(text, end="", flush=True)
    return 0


def _run_modules_record_applied(bootstrap: BootstrapHandle) -> int:
    project_dir = str(bootstrap.project_dir or "")
    if not project_dir:
        raise ConfigError(_("Project directory is not set."))
    repo_path = developing_repo_path(bootstrap)
    head_sha = git_rev_parse(repo_path, "HEAD")
    path = write_last_applied(project_dir, head_sha)
    _logger.info(
        _("Recorded developing SHA {SHA} in {PATH}.").format(SHA=head_sha, PATH=path)
    )
    return 0
