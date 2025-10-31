import sys
import os
import configparser
import datetime
from contextlib import closing, contextmanager
import io

from logger import get_module_logger
from postgres_waiter import PostgresWaiter
import cli_params

_logger = get_module_logger(__name__)

DEFAULT_TIMESTAMP_FORMAT = '%Y-%m-%d_%H-%M-%S'
DEFAULT_DB_BACKUP_FORMAT = "zip"

class OdooChecker():

    def __init__(self, config):
        _logger.info("Start Odoo Checker")
        self.odoo_dir = config["docker_odoo_dir"]
        self.odoo_config_data = config["odoo_config_data"]
        self.docker_path_odoo_conf = config["docker_path_odoo_conf"]
        self.args_dict = config["arguments"]
        self.db_lang = config["db_creation_data"]["db_lang"]
        self.db_country_code = config["db_creation_data"]["db_country_code"]
        self.db_default_admin_password = config["db_creation_data"]["db_default_admin_password"]
        self.db_default_admin_login = config["db_creation_data"]["db_default_admin_login"]
        self.db_create_demo = config["db_creation_data"]["create_demo"]
        self.db_manager_password = config.get("db_manager_password", False)
        self.sql_queries = config.get("sql_queries", [])
        self.modules_to_update = config.get("modules_to_update", [])
        self.docker_dirs_with_addons = config.get("docker_dirs_with_addons", False)

        postgres_waiter = PostgresWaiter(
            host=self.odoo_config_data["options"]["db_host"], # PostgreSQL host
            port=int(self.odoo_config_data["options"]["db_port"]), # PostgreSQL port
            timeout=60,         # Maximum waiting time in seconds
            check_interval=1    # Check interval in seconds
        )
        #TODO will add this commands for deleting cache file
        """find . -name "*.pyc" -delete"""
        """find . -name "__pycache__" -type d -exec rm -rf {} +"""
        postgres_waiter.wait_for_postgres()
        sys.path.append(self.odoo_dir)
        from passlib.hash import pbkdf2_sha512 # type: ignore
        self.pbkdf2_sha512 = pbkdf2_sha512
        import passlib # type: ignore
        self.passlib = passlib
        import odoo # type: ignore
        self.odoo = odoo
        from odoo.tools import config # type: ignore
        self.odoo_config_object = config
        from odoo.api import Environment # type: ignore
        from odoo.release import version_info as odoo_version_info # type: ignore
        self.odoo_version_info = odoo_version_info
        self.int_odoo_version = self.odoo_version_info[0]
        if self.odoo_version_info < (15, 0):
            environment_manage = Environment.manage
        else:
            @contextmanager
            def environment_manage():
                # Environment.manage is a no-op in Odoo 15+, but it
                # emits a noisy warning so let's avoid it.
                yield

        if self.odoo_version_info >= (19, 0):
            # Since 19.0 version internal strucure was changed
            import odoo.service # type: ignore
            self.odoo.service = odoo.service 

        self.environment_manage = environment_manage
        if self.db_manager_password:
            self.odoo_config_data["options"]["admin_passwd"] = self.get_encrypted_password(self.db_manager_password)
        self.create_config_file()
        self.odoo.tools.config.parse_config(["-c", self.docker_path_odoo_conf])
        # Enable database manager
        self.odoo_config_object['list_db'] = True
        os.chdir(self.odoo_dir)

        self.drop_db_name = self.args_dict.get(cli_params.DB_DROP_PARAM.replace("-", "_").strip("_"), False)
        self.get_db_list = self.args_dict.get(cli_params.GET_DB_LIST_PARAM.replace("-", "_").strip("_"), False)
        self.db_name = self.args_dict.get(cli_params.D_PARAM.replace("-", "_").strip("_"), False)
        self.db_restore_file_path = self.args_dict.get(cli_params.DB_RESTORE_PARAM.replace("-", "_").strip("_"), False)
        self.db_backup = self.args_dict.get(cli_params.DB_BACKUP_PARAM.replace("-", "_").strip("_"), False)
        self.set_admin_pass = self.args_dict.get(cli_params.SET_ADMIN_PASS_PARAM.replace("-", "_").strip("_"), False)
        self.sql_execute = self.args_dict.get(cli_params.SQL_EXECUTE_PARAM.replace("-", "_").strip("_"), False)
        self.export_po_files_lang = self.args_dict.get(cli_params.EXPORT_PO_FILES.replace("-", "_").strip("_"), False)
        
        self.all_backup_file_path = os.path.join(self.odoo_dir, "../backups/")
        
        if self.get_db_list or self.db_name:
            # Start Odoo in environment context
            with self.environment_manage():
                # Show list of current databases in system
                if self.get_db_list:
                    self.get_list_of_databases()
                # Create archive of database
                if self.db_backup and self.db_name:
                    self.backup_database()
                # Drop database
                if self.drop_db_name:
                    self.drop_database()
                # Restore database from archive
                if self.db_restore_file_path and self.db_name:
                    self.restore_database()
                # Check if database is exist and if not, system will create it
                if self.db_name:
                    self.check_if_exist_database()
                # change password and login to default for admin account
                if self.set_admin_pass and self.db_name:
                    self.set_admin_password()
                # Execute sql queries
                if self.sql_execute and self.sql_queries and self.db_name:
                    self.execute_sql_queries()
                # Export po for selected language with pot files list of modules is getting from "update_modules"
                if self.export_po_files_lang:
                    self.export_po_files_to_modules()
    
    def export_po_files_to_modules(self):
        db = self.odoo.sql_db.db_connect(self.db_name)
        for module_name in self.modules_to_update:
            module_path = ""
            for addons_dir in self.docker_dirs_with_addons:
                module_path = os.path.join(addons_dir, module_name)
                if os.path.exists(module_path):
                    break
            i18n_path = os.path.join(module_path,"i18n")
            if not os.path.exists(i18n_path):
                os.mkdir(i18n_path)
            for file_ext in ["po", "pot"]:
                with closing(io.BytesIO()) as buf:
                    with closing(db.cursor()) as cr:
                        lang = self.export_po_files_lang
                        file_name = self.export_po_files_lang.split("_")[0]
                        if file_ext == "pot":
                            lang = False
                            file_name = module_name
                        if self.int_odoo_version <= 17:
                            self.odoo.tools.trans_export(lang, [module_name], buf, "po", cr)
                        else:
                            self.odoo.tools.translate.trans_export(lang, [module_name], buf, "po", cr)
                        content = buf.getvalue()
                        full_file_path = os.path.join(i18n_path, f"{file_name}.{file_ext}")
                        with open(full_file_path, "wb") as file_to_write:
                            file_to_write.write(content)
            _logger.info(f"PO file with translation at {self.export_po_files_lang} language for module {module_name} was created")

    def create_config_file(self):
        odoo_conf = configparser.ConfigParser()
        for section in self.odoo_config_data:
            odoo_conf[section] = {}
            for key in self.odoo_config_data[section]:
                odoo_conf[section][key] = self.odoo_config_data[section][key]
        # Now we will create config file from received data threw current script argument
        with open(self.docker_path_odoo_conf, 'w') as odoo_config_file:
            odoo_conf.write(odoo_config_file)
    
    def get_id_from_ir_model_data_by_xml_id(self, xml_id):
        module_name = xml_id.split(".")[0]
        id_name = xml_id.split(".")[1]
        string_query = f""" SELECT res_id FROM ir_model_data WHERE name = '{id_name}' AND module = '{module_name}' """
        return string_query
    
    def get_encrypted_password(self, text_password):
        if self.int_odoo_version not in [11,12]:
            password_crypt = self.pbkdf2_sha512.using(rounds=1).hash(text_password)
        else:
            crypt_context = self.passlib.context.CryptContext(schemes=['pbkdf2_sha512', 'plaintext'], # type: ignore
                            deprecated=['plaintext'])
            password_crypt = crypt_context.encrypt(text_password)

        return password_crypt
    
    def change_symbols(self,string):
        new_string_name = string
        for del_symbol in ["-"," ",":"]:
            new_string_name = new_string_name.replace(del_symbol,"_")
        return new_string_name

    def backup_database(self):
        time_stamp = datetime.datetime.now().strftime(DEFAULT_TIMESTAMP_FORMAT)
        new_db_name = self.change_symbols(self.db_name)
        if isinstance(self.db_backup, bool):
            backup_filename = f"{new_db_name}_{time_stamp}"
        if isinstance(self.db_backup, str):
            backup_filename = self.db_backup
        full_path_backup_filename = os.path.join(self.all_backup_file_path, backup_filename)
        dump_stream = self.odoo.service.db.dump_db(self.db_name, None, DEFAULT_DB_BACKUP_FORMAT)
        file_arch = open(full_path_backup_filename, 'wb')
        for line in dump_stream.readlines():
            file_arch.write(line)
        file_arch.close()
    
    def restore_database(self):
        self.db_restore_file_path = os.path.join(self.all_backup_file_path, self.db_restore_file_path)
        self.odoo.service.db.restore_db(self.db_name, self.db_restore_file_path)
    
    def drop_database(self):
        if isinstance(self.drop_db_name, bool) and self.db_name:
            self.drop_db_name = self.db_name
        db_exist = self.odoo.service.db.exp_db_exist(self.drop_db_name)
        if db_exist:
            self.odoo.service.db.exp_drop(self.drop_db_name)
    
    def get_list_of_databases(self):
        list = self.odoo.service.db.list_dbs(force=True)
        final_string = ""
        for database_name in list:
            final_string += database_name + "\n"
        final_string = final_string.strip("\n")
    
    def check_if_exist_database(self):
        db_exist = self.odoo.service.db.exp_db_exist(self.db_name)
        if not db_exist:
            self.odoo.service.db.exp_create_database(
                self.db_name,
                self.db_create_demo, self.db_lang,
                user_password=self.db_default_admin_password,
                login=self.db_default_admin_login,
                country_code=self.db_country_code
            )
    
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
                    _logger.warn(f"{query} was not executed")