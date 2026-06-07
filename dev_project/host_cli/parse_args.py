"""Backward-compatible shim; host CLI lives in ``dev_project.host.cli``."""
from dev_project.shim_deprecation import warn_shim_deprecated

warn_shim_deprecated(__name__, "dev_project.host.cli.parse_args")


from dev_project.host.cli.parse_args import arg_parser, parse_args, parse_cli_args
