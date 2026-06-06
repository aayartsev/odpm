import argparse

from ..plan_cli import normalize_plan_argv
from . import params

arg_parser = argparse.ArgumentParser(
    prog="odpm",
    description="Odoo Developer Project Manager",
    epilog="Developing is not configuration",
)

arg_parser.add_argument(
    params.INIT_PARAM,
    help="""Use this param to initiate dir as odpm project. You need to set link to developing project. Example for git '--init git@github.com:aayartsev/odoo_demo_project.git' or '--init file:///your/path/to/odoo_demo_project-17/name_of_development_project_directory' for local folder""",
)

arg_parser.add_argument(
    params.BUILD_IMAGE_PARAM,
    help="Build CI image with platform sources, extra-addons, venv, and odoo.conf",
    action="store_true",
)

arg_parser.add_argument(
    params.IMAGE_TAG_PARAM,
    help="Docker tag for the CI image built with --build-image",
    type=str,
)

arg_parser.add_argument(
    params.GET_DB_LIST_PARAM,
    help="Will show list of databases",
)

arg_parser.add_argument(
    params.START_PRECOMMIT_PARAM,
    help="""Will start pre-commit for your project inside container, specified in parameter "developing_project" from file "user_settings.json" """,
    action="store_true",
)

arg_parser.add_argument(
    params.SET_ADMIN_PASS_PARAM,
    help="""When you specify the value of this parameter, the administrator account (user with id = 2) will have its password and login changed to those specified in the "db_default_admin_login" and "db_default_admin_password" parameters in the "user_settings.json" configuration file. Be sure to specify the name of the database for which you want to change the password and use the "-d database_name" parameter""",
    nargs="?",
    default=None,
    const=True,
    type=str,
)

arg_parser.add_argument(
    params.TRANSLATE_PARAM,
    help="""Will update translation for selected language, for example ru_RU or eu_US for database from -d param and for modules form "update_modules" and "init_modules" from "user_settings.json" file """,
    type=str,
)

arg_parser.add_argument(
    params.DB_DROP_PARAM,
    help="""Accept database name as parameter. Database with selected  name will be deleted. If you will use it with  params "-d", "-i", "-u", and select the same name, system will with first step delete DB and with second step will create new DB with the same name, and will install selected modules.""",
    action="store_true",
)

arg_parser.add_argument(
    params.DB_RESTORE_PARAM,
    help="""As a parameter, the name of the archive is specified, relative to the directory "BACKUP_DIR" in .env file. The DB name for restoration will be taken from the "-d" parameter.""",
    type=str,
)

arg_parser.add_argument(
    params.DB_BACKUP_PARAM,
    help="""As a parameter, the name of the archive is specified, relative to the directory "BACKUP_DIR" in .env file. The DB name for creating backup will be taken from the "-d" parameter.""",
    nargs="?",
    default=None,
    const=True,
    type=str,
)

arg_parser.add_argument(
    params.D_PARAM,
    help="""To specify the name of the database to work with. If there is no such database, it will be automatically created based on the "db_creation_data" parameter from the configuration file "user_settings.json".""",
    type=str,
)

arg_parser.add_argument(
    params.I_PARAM,
    help="""The parameter indicates that the modules specified in the "init_modules" parameter of the "user_settings.json" configuration file should be initialized.""",
    action="store_true",
)

arg_parser.add_argument(
    params.U_PARAM,
    help="""The parameter indicates that the modules specified in the "update_modules" parameter of the "user_settings.json" configuration file should be updated.""",
    action="store_true",
)

arg_parser.add_argument(
    params.T_PARAM,
    params.TEST_PARAM,
    help="""Will run tests of modules specified in "init_modules" and "update_modules", works only when using parameters "-d", "-i", "-u". If the database is being created from scratch, tests of all installed modules will be run. This may take a long time.""",
    action="store_true",
)

arg_parser.add_argument(
    params.BRANCH_PARAM,
    help="""Used together with the "--init" parameter to specify the branch of the git repository to be cloned.""",
    type=str,
)

arg_parser.add_argument(
    params.SCREENCASTS_PARAM,
    help="""Used together with the "-t" or "--test" parameter to specify saving of screencast video for tours errors. This videos will be saved to "odoo_tests" directory inside project""",
    action="store_true",
)

arg_parser.add_argument(
    params.ODOO_VERSION,
    help="""Used together with the "--init" parameter to specify Odoo version""",
    type=str,
)

arg_parser.add_argument(
    params.SQL_EXECUTE_PARAM,
    help="""Will execute sql queries that are written in "sql_queries" """,
)

arg_parser.add_argument(
    params.EXPORT_PO_FILES,
    help="""Will export pot and po file for selected language, for example ru_RU or eu_US for modules form "update_modules" from "user_settings.json" file """,
    type=str,
)

arg_parser.add_argument(
    params.VERSION,
    help="""Will show version of odpm manager""",
    action="store_true",
)

arg_parser.add_argument(
    params.ODOO_GIT_LINK_PARAM,
    help="""Used together with the "--init" parameter to specify a custom Odoo git repository URL for cloning instead of the official https://github.com/odoo/odoo.git. Accepts HTTP, SSH, or git@ links.""",
    type=str,
)

arg_parser.add_argument(
    params.PLATFORM_NAME_PARAM,
    help=f"""Used together with the "{params.INIT_PARAM}" and "{params.ODOO_GIT_LINK_PARAM}" parameters to specify custom name for Odoo fork.""",
    type=str,
)

arg_parser.add_argument(
    params.PYTHON_VERSION_PARAM,
    help="""You can set python version by this param""",
    type=str,
)

arg_parser.add_argument(
    params.DISTRO_VERSION_PARAM,
    help="""You can set Linux distro version by this param, now supported only Debian 11, 12, 13""",
    type=str,
)

arg_parser.add_argument(
    params.DISTRO_NAME_PARAM,
    help="""You can set Linux distro name by this param, now supported only Debian 11, 12, 13""",
    type=str,
)

arg_parser.add_argument(
    params.POSTGRES_VERSION_PARAM,
    help="""You can set Postgres version by this param""",
    type=str,
)

arg_parser.add_argument(
    params.REQUIREMENTS_TXT_PARAM,
    help=f"""You can set list of python packages with versions separated with comma. Example {params.REQUIREMENTS_TXT_PARAM} setuptool==80,requests==2.31.0""",
    type=str,
    default="",
)

arg_parser.add_argument(
    params.ODOO_BUILD_DATE_PARAM,
    help="""Odoo nightly build date (YYYYMMDD or YYYY-MM-DD). Resolves to the last commit on the platform branch before that day and checks it out. Overrides odoo_build_date from odpm.json. Ignored when a commit hash is set in odoo_git_link.""",
    type=str,
)

arg_parser.add_argument(
    params.PLAN_PARAM,
    help="""Show planned prepare/runtime steps without git pull, file writes, or docker compose up. Deprecated: use "odpm plan".""",
    action="store_true",
)

arg_parser.add_argument(
    params.PLAN_NO_DOCKER_PARAM,
    help="""With odpm plan: skip docker compose ps/inspect probe; compose.up will not predict --force-recreate.""",
    action="store_true",
)

arg_parser.add_argument(
    params.PLAN_SHOW_DIFF_PARAM,
    help="""With odpm plan: show unified diffs for generated project files (runtime config, compose, dockerignore).""",
    action="store_true",
)

arg_parser.add_argument(
    params.PLAN_FORMAT_PARAM,
    help="""With odpm plan: output format for the plan (table or json).""",
    choices=["table", "json"],
    default="table",
)

arg_parser.add_argument(
    params.PLAN_STRICT_PARAM,
    help="""With odpm plan: exit with code 1 when any required step would run or update.""",
    action="store_true",
)

arg_parser.add_argument(
    params.SKIP_START_PARAM,
    help="""Will generate docker-compose.yaml and exit without lounching odoo instance. After this command you can start instace with "docker compose up -d" for example""",
    nargs="?",
    default=None,
    const=True,
    type=bool,
)

arg_parser.add_argument(
    params.NO_GIT_UPDATE_PARAM,
    help="""Skip git clone, fetch, and checkout. Requires existing local platform and developing project directories (use with --skip-start to regenerate Docker files offline).""",
    action="store_true",
)

arg_parser.add_argument(
    params.UPDATE_LOCK_PARAM,
    help="""Resolve platform, developing (remote git), and full OCA-resolved dependency repositories, write .odpm/deps.lock.json, and exit without starting containers.""",
    action="store_true",
)

arg_parser.add_argument(
    params.ODOO_BIN_PARAM,
    nargs=argparse.REMAINDER,
    help="""Command to pass through as a single string""",
)

### SUBCOMMANDS ###
command_subparsers = arg_parser.add_subparsers(help="Commands")

command_subparsers.add_parser(
    params.PLAN_SUBCOMMAND,
    help="""Dry-run: show planned prepare/runtime steps (same as --plan). Example: odpm plan --skip-start""",
    add_help=False,
)

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


def parse_args(argv: list[str] | None = None):
    if argv is None:
        import sys

        argv = sys.argv[1:]
    argv_list = list(argv)
    if params.PLAN_PARAM in argv_list:
        from ..logging import get_module_logger

        get_module_logger(__name__).warning(
            '%s is deprecated; use "odpm plan" instead.',
            params.PLAN_PARAM,
        )
    return arg_parser.parse_args(normalize_plan_argv(argv_list))
