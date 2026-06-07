"""Host-side CLI argument parsing for odpm."""

from .args import OdpmCliArgs, as_cli_args
from .parse_args import arg_parser, parse_cli_args

__all__ = ["OdpmCliArgs", "arg_parser", "as_cli_args", "parse_cli_args"]
