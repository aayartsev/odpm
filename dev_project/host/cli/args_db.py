"""Host CLI flags: database operations, module init/update, and Odoo tooling."""

from __future__ import annotations

import argparse

from . import params


def add_db_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        params.GET_DB_LIST_PARAM,
        help="Will show list of databases",
    )

    parser.add_argument(
        params.START_PRECOMMIT_PARAM,
        help="""Will start pre-commit for your project inside container, specified in parameter "developing_project" from file "user_settings.json" """,
        action="store_true",
    )

    parser.add_argument(
        params.SET_ADMIN_PASS_PARAM,
        help="""When you specify the value of this parameter, the administrator account (user with id = 2) will have its password and login changed to those specified in the "db_default_admin_login" and "db_default_admin_password" parameters in the "user_settings.json" configuration file. Be sure to specify the name of the database for which you want to change the password and use the "-d database_name" parameter""",
        nargs="?",
        default=None,
        const=True,
        type=str,
    )

    parser.add_argument(
        params.TRANSLATE_PARAM,
        help="""Will update translation for selected language, for example ru_RU or eu_US for database from -d param and for modules form "update_modules" and "init_modules" from "user_settings.json" file """,
        type=str,
    )

    parser.add_argument(
        params.DB_DROP_PARAM,
        help="""Accept database name as parameter. Database with selected  name will be deleted. If you will use it with  params "-d", "-i", "-u", and select the same name, system will with first step delete DB and with second step will create new DB with the same name, and will install selected modules.""",
        action="store_true",
    )

    parser.add_argument(
        params.DB_RESTORE_PARAM,
        help="""As a parameter, the name of the archive is specified, relative to the directory "BACKUP_DIR" in .env file. The DB name for restoration will be taken from the "-d" parameter.""",
        type=str,
    )

    parser.add_argument(
        params.DB_BACKUP_PARAM,
        help="""As a parameter, the name of the archive is specified, relative to the directory "BACKUP_DIR" in .env file. The DB name for creating backup will be taken from the "-d" parameter.""",
        nargs="?",
        default=None,
        const=True,
        type=str,
    )

    parser.add_argument(
        params.D_PARAM,
        help="""To specify the name of the database to work with. If there is no such database, it will be automatically created based on the "db_creation_data" parameter from the configuration file "user_settings.json".""",
        type=str,
    )

    parser.add_argument(
        params.I_PARAM,
        help="""The parameter indicates that the modules specified in the "init_modules" parameter of the "user_settings.json" configuration file should be initialized.""",
        action="store_true",
    )

    parser.add_argument(
        params.U_PARAM,
        help="""The parameter indicates that the modules specified in the "update_modules" parameter of the "user_settings.json" configuration file should be updated.""",
        action="store_true",
    )

    parser.add_argument(
        params.T_PARAM,
        params.TEST_PARAM,
        help="""Will run tests of modules specified in "init_modules" and "update_modules", works only when using parameters "-d", "-i", "-u". If the database is being created from scratch, tests of all installed modules will be run. This may take a long time.""",
        action="store_true",
    )

    parser.add_argument(
        params.BRANCH_PARAM,
        help="""Used together with the "--init" parameter to specify the branch of the git repository to be cloned.""",
        type=str,
    )

    parser.add_argument(
        params.SCREENCASTS_PARAM,
        help="""Used together with the "-t" or "--test" parameter to specify saving of screencast video for tours errors. This videos will be saved to "odoo_tests" directory inside project""",
        action="store_true",
    )

    parser.add_argument(
        params.ODOO_VERSION,
        help="""Used together with the "--init" parameter to specify Odoo version""",
        type=str,
    )

    parser.add_argument(
        params.SQL_EXECUTE_PARAM,
        help="""Will execute sql queries that are written in "sql_queries" """,
    )

    parser.add_argument(
        params.EXPORT_PO_FILES,
        help="""Will export pot and po file for selected language, for example ru_RU or eu_US for modules form "update_modules" from "user_settings.json" file """,
        type=str,
    )

    parser.add_argument(
        params.VERSION,
        help="""Will show version of odpm manager""",
        action="store_true",
    )
