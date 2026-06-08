"""Host CLI subparser for odpm scaffold."""

from __future__ import annotations

import argparse

from . import params


def register_scaffold_subparser(command_subparsers) -> argparse.ArgumentParser:
    parser_scaffold = command_subparsers.add_parser(
        params.SCAFFOLD_SUBPARSER_PARAM,
        help="""Will create module from default template. Use it without any other parameters""",
    )
    parser_scaffold.add_argument(
        params.SCAFFOLD_SUBPARSER_MODULE_NAME_PARAM,
        type=str,
        help="""The name of the module to create, may munged in various manners to generate programmatic names (e.g. module directory name, model names, …)""",
    )
    parser_scaffold.add_argument(
        params.SCAFFOLD_SUBPARSER_T_PARAM,
        params.SCAFFOLD_SUBPARSER_TEMPLATE_NAME_PARAM,
        help="""The name of template directory, files are passed through jinja2 then copied to the destination directory""",
    )
    return parser_scaffold
