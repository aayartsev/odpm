import hashlib
import os
import shlex
from dataclasses import replace
from pathlib import Path

from . import constants
from .translations import _
from .host.cli.args import OdpmCliArgs
from .errors import ProjectDirError
from .host.cli import params as cli_params
from .logging import get_module_logger

_logger = get_module_logger(__name__)


def template_needs_upgrade(
    project_template_path: str, required_markers: list[str]
) -> bool:
    if not os.path.exists(project_template_path):
        return False
    with open(project_template_path) as reader:
        content = reader.read()
    return any(marker not in content for marker in required_markers)


def _file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as reader:
        for chunk in iter(lambda: reader.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ProjectDirManager:
    def __init__(
        self,
        start_dir_path: str,
        args: OdpmCliArgs,
        program_dir_path: str,
        *,
        sync_templates: bool = True,
    ):
        self.start_dir_path = start_dir_path
        self.project_path = start_dir_path
        self.dir_is_project = False
        self.arguments = args
        self.init = self.arguments.init
        self.sync_templates = sync_templates
        self.service_directory = os.path.join(
            self.project_path, constants.PROJECT_SERVICE_DIRECTORY
        )
        self.program_dir_path = program_dir_path
        self.home_config_dir = os.path.join(
            Path.home(), constants.CONFIG_DIR_IN_HOME_DIR
        )
        self.check_odoo_git_link()
        self.check_project_dir()
        self.bind_template_paths()
        if self.sync_templates:
            self.sync_project_templates()

    def find_project_dir_in_parents(self):
        exist_service_directory = os.path.exists(self.service_directory)
        while not exist_service_directory:
            parent_dir = os.path.abspath(os.path.join(self.project_path, os.pardir))
            if self.project_path == parent_dir:
                break
            self.project_path = parent_dir
            self.service_directory = os.path.join(
                self.project_path, constants.PROJECT_SERVICE_DIRECTORY
            )
            if self.home_config_dir == self.service_directory:
                continue
            exist_service_directory = os.path.exists(self.service_directory)

    def check_project_dir(self):
        self.find_project_dir_in_parents()
        if (
            self.project_path != self.start_dir_path
            and self.project_path in self.start_dir_path
            and not self.init
        ):
            _logger.info(
                _('Directory {START_DIR_PATH} is not a valid odpm project directory. Please run "cd {PROJECT_PATH}" to navigate to the correct location.').format(
                    START_DIR_PATH=self.start_dir_path,
                    PROJECT_PATH=self.project_path,
                )
            )
            raise ProjectDirError("", exit_code=0)
        if os.path.exists(self.service_directory):
            self.dir_is_project = True
        else:
            self.project_path = self.start_dir_path
            self.service_directory = os.path.join(
                self.project_path, constants.PROJECT_SERVICE_DIRECTORY
            )
        if not self.init and not self.dir_is_project:
            _logger.info(
                _('This is not {PROJECT_NAME} directory. If you want to init new project use "{PROJECT_NAME} {INIT_PARAM}" command').format(
                    PROJECT_NAME=constants.PROJECT_NAME,
                    INIT_PARAM=cli_params.INIT_PARAM,
                )
            )
            raise ProjectDirError("", exit_code=0)
        if self.init and not self.dir_is_project:
            self.init_project()
            if isinstance(self.init, bool):
                raise ProjectDirError("", exit_code=0)
            return
        if self.init and self.dir_is_project:
            _logger.info(
                _('This dir is already {PROJECT_NAME} project').format(
                    PROJECT_NAME=constants.PROJECT_NAME,
                )
            )
            return

    def init_project(self):
        os.makedirs(self.service_directory)
        self.bind_template_paths()
        self.sync_project_templates()

    def bind_template_paths(self) -> None:
        self.program_docker_compose_template_path = os.path.join(
            self.program_dir_path,
            constants.PROGRAM_DOCKER_COMPOSE_TEMPLATE_FILE_RELATIVE_PATH,
        )
        self.project_docker_compose_template_path = os.path.join(
            self.project_path,
            constants.PROJECT_DOCKER_COMPOSE_TEMPLATE_FILE_RELATIVE_PATH,
        )
        self.program_odoo_config_file_template_path = os.path.join(
            self.program_dir_path,
            constants.PROGRAM_ODOO_TEMPLATE_CONFIG_FILE_RELATIVE_PATH,
        )
        self.project_odoo_config_file_template_path = os.path.join(
            self.project_path, constants.PROJECT_ODOO_TEMPLATE_CONFIG_FILE_RELATIVE_PATH
        )

    def sync_project_templates(self) -> None:
        self.rebuild_docker_compose_template()
        self.rebuild_dockerignore_template()
        self.rebuild_odoo_config_file_template()
        self.rebuild_vscode_settings_json_file_template()
        self.rebuild_secrets_example_template()

    def rebuild_templates(self) -> None:
        self.bind_template_paths()
        if self.sync_templates:
            self.sync_project_templates()

    def rebuild_dockerfile_template(
        self, docker_template_filename=constants.DOCKERFILE
    ):
        program_dockerfile_template_path = os.path.join(
            self.program_dir_path,
            os.path.join(
                constants.DEV_PROJECT_DIR, "templates", docker_template_filename
            ),
        )
        project_dockerfile_template_path = os.path.join(
            self.project_path,
            os.path.join(constants.PROJECT_SERVICE_DIRECTORY, docker_template_filename),
        )
        self.ensure_project_template(
            program_dockerfile_template_path,
            project_dockerfile_template_path,
            constants.DOCKERFILE_TEMPLATE_MARKERS,
        )

    def rebuild_docker_compose_template(self):
        self.ensure_project_template(
            self.program_docker_compose_template_path,
            self.project_docker_compose_template_path,
            constants.COMPOSE_TEMPLATE_MARKERS,
        )

    def rebuild_dockerignore_template(self):
        program_dockerignore_template_path = os.path.join(
            self.program_dir_path,
            constants.PROGRAM_DOCKERIGNORE_TEMPLATE_FILE_RELATIVE_PATH,
        )
        project_dockerignore_template_path = os.path.join(
            self.project_path,
            constants.PROJECT_DOCKERIGNORE_TEMPLATE_FILE_RELATIVE_PATH,
        )
        self.ensure_project_template(
            program_dockerignore_template_path,
            project_dockerignore_template_path,
            constants.DOCKERIGNORE_TEMPLATE_MARKERS,
        )

    def rebuild_odoo_config_file_template(self):
        self.ensure_project_template(
            self.program_odoo_config_file_template_path,
            self.project_odoo_config_file_template_path,
            constants.ODOO_CONFIG_TEMPLATE_MARKERS,
        )

    def check_project_odoo_config_template(
        self, project_odoo_config_file_template_path
    ):
        return template_needs_upgrade(
            project_odoo_config_file_template_path,
            constants.ODOO_CONFIG_TEMPLATE_MARKERS,
        )

    def rebuild_vscode_settings_json_file_template(self):
        if not self.sync_templates:
            return
        program_vscode_settings_json_file_template = os.path.join(
            self.program_dir_path, constants.PROGRAM_VSCODE_SETTINGS_TEMPLATE
        )
        project_vscode_settings_json_file_template = os.path.join(
            self.project_path, constants.PROJECT_VSCODE_SETTINGS_TEMPLATE
        )
        self.generate_project_template_files(
            program_vscode_settings_json_file_template,
            project_vscode_settings_json_file_template,
        )

    def rebuild_secrets_example_template(self) -> None:
        if not self.sync_templates:
            return
        program_template = os.path.join(
            self.program_dir_path,
            constants.DEV_PROJECT_DIR,
            "templates",
            "secrets.example.json",
        )
        project_template = os.path.join(
            self.project_path, constants.ODPM_SECRETS_EXAMPLE_REL_PATH
        )
        self.generate_project_template_files(program_template, project_template)

    def ensure_project_template(
        self,
        program_template_file: str,
        project_template_file: str,
        required_markers: list[str] | None = None,
    ) -> None:
        if not self.sync_templates:
            return
        needs_refresh = False
        if os.path.isfile(program_template_file) and os.path.isfile(project_template_file):
            if _file_sha256(program_template_file) != _file_sha256(project_template_file):
                needs_refresh = True
        if required_markers and template_needs_upgrade(
            project_template_file, required_markers
        ):
            needs_refresh = True
        if needs_refresh and os.path.isfile(project_template_file):
            _logger.info(
                "Upgrading %s to current odpm template",
                project_template_file,
            )
            os.remove(project_template_file)
        self.generate_project_template_files(
            program_template_file, project_template_file
        )

    def generate_project_template_files(
        self, program_template_file, project_template_file
    ):
        with open(program_template_file, encoding="utf-8") as f:
            lines = f.readlines()
        content = "".join(lines)
        for replace_phrase in {
            constants.MESSAGE_MARKER: _('If you want drop this file to default values, just delete it'),
        }.items():
            content = content.replace(replace_phrase[0], replace_phrase[1])
        if not os.path.exists(project_template_file):
            with open(project_template_file, "w", encoding="utf-8") as writer:
                writer.write(content)

    def check_odoo_git_link(self):
        if self.arguments.odoo_git_link and not self.init:
            message = _('The {ODOO_GIT_LINK_PARAM} parameter can only be used together with the {INIT_PARAM} parameter').format(
                ODOO_GIT_LINK_PARAM=cli_params.ODOO_GIT_LINK_PARAM,
                INIT_PARAM=cli_params.INIT_PARAM,
            )
            _logger.error(message)
            raise ProjectDirError(message)
        if not self.arguments.odoo_git_link:
            self.arguments = replace(
                self.arguments, odoo_git_link=constants.ODOO_GIT_LINK
            )

    def get_shortest_cd_command(self, current_dir: str, target_dir: str) -> str:
        """
        Returns the shortest 'cd' command to navigate from current_dir to target_dir.
        Automatically selects the optimal path (relative vs. absolute) based on length.
        """
        curr = Path(current_dir).resolve()
        tgt = Path(target_dir).resolve()

        if curr == tgt:
            return "cd ."

        # Attempt to compute the relative path
        try:
            rel_path = os.path.relpath(tgt, curr)
        except ValueError:
            # On Windows, this raises ValueError if paths are on different drives (e.g., C:\ and D:\)
            rel_path = None

        abs_path = str(tgt)

        # Select the shorter option (fallback to absolute path if relative is unavailable)
        best_path = rel_path if rel_path and len(rel_path) < len(abs_path) else abs_path

        # Quote spaces and special characters for safe terminal execution
        return f"cd {shlex.quote(best_path)}"
