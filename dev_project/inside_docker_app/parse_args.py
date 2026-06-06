"""Backward-compatible shim; host CLI lives in dev_project.host_cli."""

from dev_project.host_cli.parse_args import arg_parser, parse_args

__all__ = ["arg_parser", "parse_args"]
