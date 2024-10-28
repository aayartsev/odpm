import configparser
import json
import base64
import pathlib
import os

from . import constants
from .inside_docker_app import cli_params
from .host_config import Config

class StartStringBuilder():

    def __init__(self, config: Config) -> None:
        self.config = config
        self.args = self.config.arguments
        self.config.start_string = self.get_start_string()
    
    def get_base64_string_config(self) -> str:
        data = self.config.config_to_json()
        config_base64_data = base64.b64encode(data)
        return config_base64_data.decode()
    
    def get_start_string(self) -> str:
        # Reading of config file
        odoo_config = configparser.ConfigParser()
        odoo_config.read(
            self.config.path_odoo_conf
        )
        # Build string of all addons directories
        addons_string = ",".join(
            self.config.docker_dirs_with_addons
        )
        odoo_config["options"]["addons_path"] = addons_string

        data_dir = str(pathlib.PurePosixPath(self.config.docker_project_dir, ".local/share/Odoo"))
        odoo_config["options"]["data_dir"] = data_dir
        self.config.odoo_config_data = {s:dict(odoo_config.items(s)) for s in odoo_config.sections()}
        start_python_command = f"""python3 -u -m debugpy --listen 0.0.0.0:{constants.DEBUGGER_DOCKER_PORT} {self.config.docker_odoo_dir}/odoo-bin -c {self.config.docker_project_dir}/odoo.conf --limit-time-real 99999"""
        db_name = self.args.d
        translate_lang = self.args.translate
        install_pip = self.args.pip_install
        start_pre_commit = self.args.start_precommit
        build_image = self.args.build_image
        dev_mode = self.config.dev_mode or False
        
        if build_image:
            self.config.project_env.build_image()
            exit()

        if install_pip:
            pip_install_command = f"""cd {self.config.docker_project_dir} && python3 -m venv {self.config.docker_venv_dir} && . {pathlib.PurePosixPath(self.config.docker_venv_dir, "bin", "activate")} && wget -O odoo_requirements.txt https://raw.githubusercontent.com/odoo/odoo/{self.config.odoo_version}/requirements.txt && python3 -m pip install -r odoo_requirements.txt && python3 -m pip install {" ".join([req for req in self.config.requirements_txt])}"""
            start_string = f"""bash -c '{pip_install_command}'"""
            return start_string
        
        if start_pre_commit:
            start_string = f"""/bin/bash -c 'cd {self.config.docker_odoo_project_dir_path} && ls && git config --global --add safe.directory {self.config.docker_odoo_project_dir_path} && pre-commit run --all-files'"""
            return start_string

        if db_name:
            start_python_command +=  f" {cli_params.D_PARAM} {db_name}"

        if self.args.i:
            start_python_command += f""" {cli_params.I_PARAM} {self.config.init_modules}"""

        if self.args.u:
            start_python_command += f""" {cli_params.U_PARAM} {self.config.update_modules}"""

        if self.args.test:
            start_python_command += f" --test-enable --stop-after-init"
            if self.args.screencasts:
                start_python_command += f""" {cli_params.SCREENCASTS_PARAM} {self.config.docker_temp_tests_dir}"""
                

        if translate_lang:
            start_python_command += f" --language {translate_lang} --load-language {translate_lang} --i18n-overwrite"

        if dev_mode:
            start_python_command += f" --dev {dev_mode}"

        start_main = " && ".join([
            f"""cd {self.config.docker_project_dir}""",
            f"""python3 {pathlib.PurePosixPath(self.config.docker_inside_app,"main.py")} {cli_params.CONFIG_BASE64_DATA} {self.get_base64_string_config()}""",
            f""". {pathlib.PurePosixPath(self.config.docker_venv_dir,"bin", "activate")}""",
            f"""{start_python_command}""",
        ])
        start_string = f"""bash -c '{start_main}'"""
        return start_string