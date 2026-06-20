"""Host CLI flags: project init, CI image build, platform and environment versions."""

from __future__ import annotations

import argparse

from . import params


def add_init_core_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        params.INIT_PARAM,
        help="""Use this param to initiate dir as odpm project. You need to set link to developing project. Example for git '--init https://github.com/aayartsev/odoo_demo_project.git --branch 19.0' or '--init file:///your/path/to/odoo_demo_project-19' for local folder""",
    )

    parser.add_argument(
        params.BUILD_IMAGE_PARAM,
        help="Build CI image with platform sources, extra-addons, venv, and odoo.conf",
        action="store_true",
    )

    parser.add_argument(
        params.IMAGE_TAG_PARAM,
        help="Docker tag for the CI image built with --build-image",
        type=str,
    )


def add_platform_env_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        params.ODOO_GIT_LINK_PARAM,
        help="""Used together with the "--init" parameter to specify a custom Odoo git repository URL for cloning instead of the official https://github.com/odoo/odoo.git. Accepts HTTP, SSH, or git@ links.""",
        type=str,
    )

    parser.add_argument(
        params.PLATFORM_NAME_PARAM,
        help=f"""Used together with the "{params.INIT_PARAM}" and "{params.ODOO_GIT_LINK_PARAM}" parameters to specify custom name for Odoo fork.""",
        type=str,
    )

    parser.add_argument(
        params.PYTHON_VERSION_PARAM,
        help="""You can set python version by this param""",
        type=str,
    )

    parser.add_argument(
        params.DISTRO_VERSION_PARAM,
        help="""You can set Linux distro version by this param, now supported only Debian 11, 12, 13""",
        type=str,
    )

    parser.add_argument(
        params.DISTRO_NAME_PARAM,
        help="""You can set Linux distro name by this param, now supported only Debian 11, 12, 13""",
        type=str,
    )

    parser.add_argument(
        params.POSTGRES_VERSION_PARAM,
        help="""You can set Postgres version by this param""",
        type=str,
    )

    parser.add_argument(
        params.REQUIREMENTS_TXT_PARAM,
        help=f"""You can set list of python packages with versions separated with comma. Example {params.REQUIREMENTS_TXT_PARAM} setuptool==80,requests==2.31.0""",
        type=str,
        default="",
    )

    parser.add_argument(
        params.ODOO_BUILD_DATE_PARAM,
        help="""Odoo nightly build date (YYYYMMDD or YYYY-MM-DD). Resolves to the last commit on the platform branch before that day and checks it out. Overrides odoo_build_date from odpm.json. Ignored when a commit hash is set in odoo_git_link.""",
        type=str,
    )

    parser.add_argument(
        params.SECRETS_FILE_PARAM,
        help="""Import secrets from a JSON file into .odpm/secrets.json (schema v1). Works with --init and on any run.""",
        type=str,
    )
