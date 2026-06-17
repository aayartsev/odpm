"""Parse checker CLI flags and run post-bootstrap Odoo operations."""

from __future__ import annotations

from dataclasses import dataclass

from ...container_config import ContainerConfig
from ..params import (
    DB_BACKUP_PARAM,
    DB_DROP_PARAM,
    DB_RESTORE_PARAM,
    D_PARAM,
    EXPORT_PO_FILES,
    GET_DB_LIST_PARAM,
    SET_ADMIN_PASS_PARAM,
    SQL_EXECUTE_PARAM,
)
from .admin_ops import OdooAdminOps
from .db_ops import OdooDbOps
from .i18n_ops import OdooI18nOps
from .postgres_waiter import PostgresWaiter
from ...database.record import record_last_run_from_container
from .runtime import LoadedOdooRuntime
from .sql_runner import OdooSqlRunner


def _arg_key(param: str) -> str:
    return param.replace("-", "_").strip("_")


@dataclass(frozen=True)
class CheckerCliFlags:
    drop_db_name: str | bool
    get_db_list: str | bool
    db_name: str | bool
    db_restore_file_path: str | bool
    db_backup: str | bool
    set_admin_pass: str | bool
    sql_execute: str | bool
    export_po_files_lang: str | bool


def checker_cli_flags(args_dict: dict) -> CheckerCliFlags:
    return CheckerCliFlags(
        drop_db_name=args_dict.get(_arg_key(DB_DROP_PARAM), False),
        get_db_list=args_dict.get(_arg_key(GET_DB_LIST_PARAM), False),
        db_name=args_dict.get(_arg_key(D_PARAM), False),
        db_restore_file_path=args_dict.get(
            _arg_key(DB_RESTORE_PARAM), False
        ),
        db_backup=args_dict.get(_arg_key(DB_BACKUP_PARAM), False),
        set_admin_pass=args_dict.get(_arg_key(SET_ADMIN_PASS_PARAM), False),
        sql_execute=args_dict.get(_arg_key(SQL_EXECUTE_PARAM), False),
        export_po_files_lang=args_dict.get(
            _arg_key(EXPORT_PO_FILES), False
        ),
    )


def wait_for_postgres(config: ContainerConfig) -> None:
    options = config.odoo_config_data["options"]
    postgres_waiter = PostgresWaiter(
        host=options["db_host"],
        port=int(options["db_port"]),
        timeout=60,
        check_interval=1,
    )
    postgres_waiter.wait_for_postgres()
    postgres_waiter.verify_postgres_credentials(
        dbname="postgres",
        user=options["db_user"],
        password=options["db_password"],
    )
    record_last_run_from_container(config)


def run_checker_operations(
    config: ContainerConfig,
    flags: CheckerCliFlags,
    runtime: LoadedOdooRuntime,
    *,
    db_ops: OdooDbOps,
    admin_ops: OdooAdminOps,
    sql_runner: OdooSqlRunner,
    i18n_ops: OdooI18nOps,
) -> None:
    if not (flags.get_db_list or flags.db_name):
        return

    with runtime.environment_manage():
        if flags.get_db_list:
            db_ops.get_list_of_databases()
        if flags.db_backup and flags.db_name:
            db_ops.backup_database(flags.db_name, flags.db_backup)
        if flags.drop_db_name:
            db_ops.drop_database(flags.drop_db_name, flags.db_name)
        if flags.db_restore_file_path and flags.db_name:
            db_ops.restore_database(flags.db_name, flags.db_restore_file_path)
        if flags.db_name:
            db_ops.ensure_database_exists(flags.db_name)
        if flags.set_admin_pass and flags.db_name:
            admin_ops.set_admin_password(
                flags.db_name,
                admin_login=config.db_creation_data.db_default_admin_login,
                admin_password=config.db_creation_data.db_default_admin_password,
            )
        if flags.sql_execute and config.sql_queries and flags.db_name:
            sql_runner.execute_queries(flags.db_name, config.sql_queries)
        if flags.export_po_files_lang:
            i18n_ops.export_po_files(
                flags.db_name,
                flags.export_po_files_lang,
                config.modules_to_update,
                config.docker_dirs_with_addons or (),
            )
