"""Thin orchestrator: postgres wait → Odoo runtime → dispatch CLI operations."""

from __future__ import annotations

from ...container_config import ContainerConfig
from ...logging import get_module_logger
from .admin_ops import OdooAdminOps, encrypt_odoo_password
from .db_ops import DbCreationParams, OdooDbOps
from .dispatch import checker_cli_flags, run_checker_operations, wait_for_postgres
from .i18n_ops import OdooI18nOps
from .runtime import apply_odoo_config, load_odoo_runtime
from .sql_runner import OdooSqlRunner

_logger = get_module_logger(__name__)


class OdooChecker:
    def __init__(self, config: ContainerConfig):
        _logger.info("Start Odoo Checker")
        flags = checker_cli_flags(config.arguments)
        wait_for_postgres(config, flags.db_name)

        from passlib.hash import pbkdf2_sha512  # type: ignore
        import passlib  # type: ignore

        runtime = load_odoo_runtime(
            platform_name=config.platform_name,
            odoo_dir=config.docker_odoo_dir,
        )
        if config.db_manager_password:
            config.odoo_config_data["options"]["admin_passwd"] = encrypt_odoo_password(
                config.db_manager_password,
                int_odoo_version=runtime.int_odoo_version,
                pbkdf2_sha512=pbkdf2_sha512,
                passlib=passlib,
            )
        apply_odoo_config(
            runtime,
            odoo_config_data=config.odoo_config_data,
            docker_path_odoo_conf=config.docker_path_odoo_conf,
        )

        run_checker_operations(
            config,
            flags,
            runtime,
            db_ops=OdooDbOps(
                runtime.odoo,
                odoo_dir=config.docker_odoo_dir,
                creation=DbCreationParams(
                    create_demo=config.db_creation_data.create_demo,
                    db_lang=config.db_creation_data.db_lang,
                    db_default_admin_password=config.db_creation_data.db_default_admin_password,
                    db_default_admin_login=config.db_creation_data.db_default_admin_login,
                    db_country_code=config.db_creation_data.db_country_code,
                ),
            ),
            admin_ops=OdooAdminOps(
                runtime.odoo,
                int_odoo_version=runtime.int_odoo_version,
                odoo_version_info=runtime.odoo_version_info,
                pbkdf2_sha512=pbkdf2_sha512,
                passlib=passlib,
            ),
            sql_runner=OdooSqlRunner(runtime.odoo),
            i18n_ops=OdooI18nOps(
                runtime.odoo, int_odoo_version=runtime.int_odoo_version
            ),
        )
