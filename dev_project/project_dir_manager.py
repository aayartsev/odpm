import os
from pathlib import Path
from argparse import Namespace

from .inside_docker_app import cli_params
from . import constants
from . import translations

from .inside_docker_app.logger import get_module_logger

_logger = get_module_logger(__name__)

class ProjectDirManager():

    def __init__(self, start_dir_path: str, args: Namespace, program_dir_path: str):
        self.start_dir_path = start_dir_path
        self.project_path = start_dir_path
        self.dir_is_project = False
        self.args = args
        self.init = self.args.init
        self.service_directory = os.path.join(self.project_path, constants.PROJECT_SERVICE_DIRECTORY)
        self.program_dir_path = program_dir_path
        self.home_config_dir = os.path.join(Path.home(), constants.CONFIG_DIR_IN_HOME_DIR)
    
    def find_project_dir_in_parents(self):
        exist_service_directory = os.path.exists(self.service_directory)
        while not exist_service_directory:
            parent_dir = os.path.abspath(os.path.join(self.project_path, os.pardir))
            if self.project_path == parent_dir:
                break
            self.project_path = parent_dir
            self.service_directory = os.path.join(self.project_path, constants.PROJECT_SERVICE_DIRECTORY)
            if self.home_config_dir == self.service_directory:
                continue
            exist_service_directory = os.path.exists(self.service_directory)

    def check_project_dir(self):
        self.find_project_dir_in_parents()
        if os.path.exists(self.service_directory):
            self.dir_is_project = True
        else:
            self.project_path = self.start_dir_path
            self.service_directory = os.path.join(self.project_path, constants.PROJECT_SERVICE_DIRECTORY)
        if not self.init and not self.dir_is_project:
            _logger.info(translations.get_translation(translations.THIS_IS_NOT_PROJECT_DIRECTORY).format(
                        PROJECT_NAME=constants.PROJECT_NAME,
                        INIT_PARAM=cli_params.INIT_PARAM,
                    ))
            exit()
        if self.init and not self.dir_is_project:
            self.init_project()
            if isinstance(self.init, bool):
                exit()
            return
        if self.init and self.dir_is_project:
            _logger.info(translations.get_translation(translations.ALREADY_INITED_PROJECT).format(
                        PROJECT_NAME=constants.PROJECT_NAME,
                    ))
            return
        self.rebuild_templates()


    def init_project(self):
        os.makedirs(self.service_directory)
        self.rebuild_templates()
    
    def rebuild_templates(self):
        self.rebuild_docker_compose_template()
        self.rebuild_odoo_config_file_template()
        self.rebuild_vscode_settings_json_file_template()
    
    def rebuild_dockerfile_template(self, docker_template_filename=constants.DOCKERFILE):
        program_dockerfile_template_path = os.path.join(
            self.program_dir_path,
            os.path.join(constants.DEV_PROJECT_DIR, "templates", docker_template_filename)
        )
        project_dockerfile_template_path = os.path.join(
            self.project_path,
            os.path.join(constants.PROJECT_SERVICE_DIRECTORY, docker_template_filename)
        )
        self.generate_project_template_files(program_dockerfile_template_path, project_dockerfile_template_path)
    
    def rebuild_docker_compose_template(self):
        program_docker_compose_template_path = os.path.join(self.program_dir_path, constants.PROGRAM_DOCKER_COMPOSE_TEMPLATE_FILE_RELATIVE_PATH)
        project_docker_compose_template_path = os.path.join(self.project_path, constants.PROJECT_DOCKER_COMPOSE_TEMPLATE_FILE_RELATIVE_PATH)
        self.generate_project_template_files(program_docker_compose_template_path, project_docker_compose_template_path)
    
    def rebuild_odoo_config_file_template(self):
        program_odoo_config_file_template_path = os.path.join(self.program_dir_path, constants.PROGRAM_ODOO_TEMPLATE_CONFIG_FILE_RELATIVE_PATH)
        project_odoo_config_file_template_path = os.path.join(self.project_path, constants.PROJECT_ODOO_TEMPLATE_CONFIG_FILE_RELATIVE_PATH)
        if self.check_project_odoo_config_template(project_odoo_config_file_template_path):
            os.remove(project_odoo_config_file_template_path)
        self.generate_project_template_files(program_odoo_config_file_template_path, project_odoo_config_file_template_path)
    
    def check_project_odoo_config_template(self, project_odoo_config_file_template_path):
        odoo_config_need_to_rebuild = False
        if os.path.exists(project_odoo_config_file_template_path):
            with open(project_odoo_config_file_template_path) as f:
                lines = f.readlines()
            content = "".join(lines)
            for searchable_pattern in [
                    constants.DO_NOT_CHANGE_PARAM,
                    constants.ADMIN_PASSWD_MESSAGE,
                    constants.POSTGRES_ODOO_USER_MARKER,
                    constants.POSTGRES_ODOO_PASS_MARKER,
                    constants.POSTGRES_ODOO_HOST_MARKER,
                    constants.POSTGRES_ODOO_PORT_MARKER,
                    constants.ODOO_PORT_MARKER,
                ]:
                if searchable_pattern not in content:
                    odoo_config_need_to_rebuild = True
        else:
            odoo_config_need_to_rebuild = True
        return odoo_config_need_to_rebuild

    
    def rebuild_vscode_settings_json_file_template(self):
        program_vscode_settings_json_file_template = os.path.join(self.program_dir_path, constants.PROGRAM_VSCODE_SETTINGS_TEMPLATE)
        project_vscode_settings_json_file_template = os.path.join(self.project_path, constants.PROJECT_VSCODE_SETTINGS_TEMPLATE)
        self.generate_project_template_files(program_vscode_settings_json_file_template, project_vscode_settings_json_file_template)

    def generate_project_template_files(self, program_template_file, project_template_file):
        with open(program_template_file) as f:
            lines = f.readlines()
        content = "".join(lines)
        for replace_phrase in {
                constants.MESSAGE_MARKER: translations.get_translation(translations.MESSAGE_FOR_TEMPLATES),
            }.items():
            content = content.replace(replace_phrase[0], replace_phrase[1])
        if not os.path.exists(project_template_file):
            with open(project_template_file, 'w') as writer:
                writer.write(content)
