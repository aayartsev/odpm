"""Console entry point for ``odpm`` (pip) and legacy ``odpm.py`` wrapper."""

from __future__ import annotations

import os
import sys

from .translations import _
from .host.locale_bootstrap import bootstrap_host_locale
from .host.cli.parse_args import parse_cli_args
from .logging import get_module_logger
from .odpm_pipeline import OdpmPipeline
from .program_dir import resolve_program_dir

_logger = get_module_logger(__name__)


def main(program_dir: str | None = None) -> None:
    bootstrap_host_locale(os.getcwd())
    if hasattr(os, "geteuid") and os.geteuid() == 0:
        _logger.error(_('Running with sudo/root privileges is not permitted.'))
        sys.exit(1)

    OdpmPipeline(parse_cli_args(), resolve_program_dir(program_dir)).run()
