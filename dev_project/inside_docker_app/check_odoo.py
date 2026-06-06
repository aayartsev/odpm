import importlib
import io
import os
import sys
from contextlib import closing, contextmanager

from ..container_config import ContainerConfig
from . import cli_params
from .logger import get_module_logger
from .odoo_db_ops import DbCreationParams, OdooDbOps
from .postgres_waiter import PostgresWaiter
from .utils import write_odoo_config_data_to_file

_logger = get_module_logger(__name__)

USED_ODOO_SUBMODULES = ["tools", "api", "service"]


class OdooChecker:
    def __init__(self, config: ContainerConfig):
        _logger.info("Start Odoo Checker")
        self.odoo_dir = config.docker_odoo_dir
        self.odoo_config_data = config.odoo_config_data
        self.docker_path_odoo_conf = config.docker_path_odoo_conf
        self.args_dict = config.arguments
        self.platform_name = config.platform_name
        self.db_lang = config.db_creation_data.db_lang
        self.db_country_code = config.db_creation_data.db_country_code
        self.db_default_admin_password = config.db_creation_data.db_default_admin_password
        self.db_default_admin_login = config.db_creation_data.db_default_admin_login
        self.db_create_demo = config.db_creation_data.create_demo
        self.db_manager_password = config.db_manager_password or False
        self.sql_queries = config.sql_queries
        self.modules_to_update = config.modules_to_update
        self.docker_dirs_with_addons = config.docker_dirs_with_addons or False

        self.drop_db_name = self.args_dict.get(
            cli_params.DB_DROP_PARAM.replace("-", "_").strip("_"), False
        )
        self.get_db_list = self.args_dict.get(
            cli_params.GET_DB_LIST_PARAM.replace("-", "_").strip("_"), False
        )
        self.db_name = self.args_dict.get(
            cli_params.D_PARAM.replace("-", "_").strip("_"), False
        )
        self.db_restore_file_path = self.args_dict.get(
            cli_params.DB_RESTORE_PARAM.replace("-", "_").strip("_"), False
        )
        self.db_backup = self.args_dict.get(
            cli_params.DB_BACKUP_PARAM.replace("-", "_").strip("_"), False
        )
        self.set_admin_pass = self.args_dict.get(
            cli_params.SET_ADMIN_PASS_PARAM.replace("-", "_").strip("_"), False
        )
        self.sql_execute = self.args_dict.get(
            cli_params.SQL_EXECUTE_PARAM.replace("-", "_").strip("_"), False
        )
        self.export_po_files_lang = self.args_dict.get(
            cli_params.EXPORT_PO_FILES.replace("-", "_").strip("_"), False
        )

        odoo_src_dir = os.path.abspath(self.odoo_dir)
        if odoo_src_dir not in sys.path:
            sys.path.insert(0, odoo_src_dir)

        postgres_waiter = PostgresWaiter(
            host=self.odoo_config_data["options"]["db_host"],
            port=int(self.odoo_config_data["options"]["db_port"]),
            timeout=60,
            check_interval=1,
        )
        postgres_waiter.wait_for_postgres()
        if self.db_name:
            postgres_waiter.wait_for_postgres_db(
                dbname="postgres",
                user=self.odoo_config_data["options"]["db_user"],
                password=self.odoo_config_data["options"]["db_password"],
                max_attempts=None,
            )

        from passlib.hash import pbkdf2_sha512  # type: ignore

        self.pbkdf2_sha512 = pbkdf2_sha512
        import passlib  # type: ignore

        self.passlib = passlib
        self.odoo = importlib.import_module(self.platform_name)
        for submodule in USED_ODOO_SUBMODULES:
            self.add_attrs_to_self_odoo(submodule)
        self.odoo_config_object = getattr(self.odoo.tools, "config")
        Environment = getattr(self.odoo.api, "Environment")
        odoo_version_info = getattr(self.odoo.release, "version_info")
        self.odoo_version_info = odoo_version_info
        self.int_odoo_version = self.odoo_version_info[0]
        if self.odoo_version_info < (15, 0):
            environment_manage = Environment.manage
        else:

            @contextmanager
            def environment_manage():
                yield

        self.environment_manage = environment_manage
        if self.db_manager_password:
            self.odoo_config_data["options"]["admin_passwd"] = (
                self.get_encrypted_password(self.db_manager_password)
            )
        self.create_config_file()
        self.odoo.tools.config.parse_config(["-c", self.docker_path_odoo_conf])
        self.odoo_config_object["list_db"] = True

        self.db_ops = OdooDbOps(
            self.odoo,
            odoo_dir=self.odoo_dir,
            creation=DbCreationParams(
                create_demo=self.db_create_demo,
                db_lang=self.db_lang,
                db_default_admin_password=self.db_default_admin_password,
                db_default_admin_login=self.db_default_admin_login,
                db_country_code=self.db_country_code,
            ),
        )

        if self.get_db_list or self.db_name:
            with self.environment_manage():
                if self.get_db_list:
                    self.db_ops.get_list_of_databases()
                if self.db_backup and self.db_name:
                    self.db_ops.backup_database(self.db_name, self.db_backup)
                if self.drop_db_name:
                    self.db_ops.drop_database(self.drop_db_name, self.db_name)
                if self.db_restore_file_path and self.db_name:
                    self.db_ops.restore_database(
                        self.db_name, self.db_restore_file_path
                    )
                if self.db_name:
                    self.db_ops.ensure_database_exists(self.db_name)
                if self.set_admin_pass and self.db_name:
                    self.set_admin_password()
                if self.sql_execute and self.sql_queries and self.db_name:
                    self.execute_sql_queries()
                if self.export_po_files_lang:
                    self.export_po_files_to_modules()

    def add_attrs_to_self_odoo(self, attr_name):
        if not getattr(self.odoo, attr_name, None):
            setattr(
                self.odoo,
                attr_name,
                importlib.import_module(f"{self.platform_name}.{attr_name}"),
            )

    def export_po_files_to_modules(self):
        db = self.odoo.sql_db.db_connect(self.db_name)
        for module_name in self.modules_to_update:
            module_path = ""
            for addons_dir in self.docker_dirs_with_addons:
                module_path = os.path.join(addons_dir, module_name)
                if os.path.exists(module_path):
                    break
            i18n_path = os.path.join(module_path, "i18n")
            if not os.path.exists(i18n_path):
                os.mkdir(i18n_path)
            for file_ext in ["po", "pot"]:
                with closing(io.BytesIO()) as buf:
                    with closing(db.cursor()) as cr:
                        env = self.odoo.api.Environment(cr, self.odoo.SUPERUSER_ID, {})
                        lang = self.export_po_files_lang
                        file_name = self.export_po_files_lang.split("_")[0]
                        if file_ext == "pot":
                            lang = False
                            file_name = module_name
                        if self.int_odoo_version <= 17:
                            self.odoo.tools.trans_export(
                                lang, [module_name], buf, "po", cr
                            )
                        else:
                            if self.int_odoo_version == 18:
                                self.odoo.tools.translate.trans_export(
                                    lang, [module_name], buf, "po", cr
                                )
                            else:
                                self.odoo.tools.translate.trans_export(
                                    lang, [module_name], buf, "po", env
                                )
                        content = buf.getvalue()
                        full_file_path = os.path.join(
                            i18n_path, f"{file_name}.{file_ext}"
                        )
                        with open(full_file_path, "wb") as file_to_write:
                            file_to_write.write(content)
            _logger.info(
                f"PO file with translation at {self.export_po_files_lang} language for module {module_name} was created"
            )

    def create_config_file(self):
        write_odoo_config_data_to_file(self.odoo_config_data, self.docker_path_odoo_conf)

    def get_id_from_ir_model_data_by_xml_id(self, xml_id):
        module_name = xml_id.split(".")[0]
        id_name = xml_id.split(".")[1]
        string_query = f""" SELECT res_id FROM ir_model_data WHERE name = '{id_name}' AND module = '{module_name}' """
        return string_query

    def get_encrypted_password(self, text_password):
        if self.int_odoo_version not in [11, 12]:
            password_crypt = self.pbkdf2_sha512.using(rounds=1).hash(text_password)
        else:
            crypt_context = self.passlib.context.CryptContext(
                schemes=["pbkdf2_sha512", "plaintext"],  # type: ignore
                deprecated=["plaintext"],
            )
            password_crypt = crypt_context.encrypt(text_password)

        return password_crypt

    def set_admin_password(self):
        new_password = self.db_default_admin_password
        password_crypt_field = "password"
        admin_xml_id = "base.user_admin"
        password_crypt = self.get_encrypted_password(new_password)
        if self.odoo_version_info[0] == 11:
            password_crypt_field = "password_crypt"
            admin_xml_id = "base.user_root"
        xml_id_query = self.get_id_from_ir_model_data_by_xml_id(admin_xml_id)
        sql_command = f"""
        UPDATE res_users SET
            {password_crypt_field} = '{password_crypt}',
            login = '{self.db_default_admin_login}'
        WHERE id in ({xml_id_query});
        """
        db = self.odoo.sql_db.db_connect(self.db_name)
        with closing(db.cursor()) as cr:
            cr.execute(sql_command, log_exceptions=True)
            cr.commit()

    def execute_sql_queries(self):
        db = self.odoo.sql_db.db_connect(self.db_name)
        with closing(db.cursor()) as cr:
            for query in self.sql_queries:
                try:
                    cr.execute(query, log_exceptions=True)
                    cr.commit()
                except:
                    _logger.warning(f"{query} was not executed")
