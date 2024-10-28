import os
import subprocess
import json
import shutil

import pathlib
from pathlib import Path

from typing import NamedTuple
from typing import TypedDict
from typing import Literal

from .handle_odoo_project_git_link import HandleOdooProjectLink
from . import constants
from . import translations
from .host_config import Config
from .protocols import CreateProjectEnvironmentProtocol
from .inside_docker_app.utils import delete_files_in_directory, get_direct_link_to_download_from_yadisk, download_file, un_zip_file_to_directory

from .inside_docker_app.logger import get_module_logger

_logger = get_module_logger(__name__)
_ = translations._

class MappedPath(NamedTuple):
    local: str
    docker: str

class MappedSources(NamedTuple):
    local: str
    remote: str

class DebuggerPathRecord(TypedDict):
    localRoot: str
    remoteRoot: str

class DebuggerUnit(TypedDict):
    name: str
    type: Literal["python"]
    request: Literal["attach"]
    port: int
    host: Literal["localhost"]
    pathMappings: list[DebuggerPathRecord]

class CreateProjectEnvironment(CreateProjectEnvironmentProtocol):

    def __init__(self, config: Config):
        self.config = config
        self.user_env = self.config.user_env
        self.config.project_env = self


    def map_folders(self) -> None:
        self.mapped_folders = [
            MappedPath(local=self.user_env.odoo_src_dir, docker=self.config.docker_odoo_dir),
            MappedPath(local=self.config.venv_dir, docker=self.config.docker_venv_dir),
            MappedPath(local=self.config.odoo_tests_dir, docker=self.config.docker_temp_tests_dir),
            MappedPath(local=os.path.join(self.config.program_dir, constants.DEV_PROJECT_DIR), docker=self.config.docker_dev_project_dir),
            MappedPath(local=self.user_env.backups, docker=self.config.docker_backups_dir),
            MappedPath(local=os.path.join(self.config.docker_home, ".local"), docker=str(pathlib.PurePosixPath(self.config.docker_project_dir, ".local"))),
            MappedPath(local=os.path.join(self.config.docker_home, ".cache"), docker=str(pathlib.PurePosixPath(self.config.docker_project_dir, ".cache"))),
        ]
        if self.config.developing_project.project_path:
            self.mapped_folders.append(
                MappedPath(local=self.config.developing_project.project_path, docker=self.config.docker_odoo_project_dir_path),
            )
        if self.config.use_oca_dependencies:
            self.check_oca_dependencies(self.config.developing_project)
        for dependency_string in self.config.dependencies:
            dependency_project = self.config.handle_git_link(dependency_string)
            if not dependency_project.is_cloned:
                continue
            if self.config.use_oca_dependencies:
                self.check_oca_dependencies(dependency_project)
            list_of_subprojects = self.config.check_project_for_subprojects(dependency_project.project_path)
            docker_dependency_project_path = str(pathlib.PurePosixPath(self.config.docker_extra_addons, dependency_project.inside_docker_path))
            self.config.dependencies_projects.append(dependency_project)
            self.config.dependencies_dirs.append(dependency_project.project_path)
            docker_dir_with_addons = docker_dependency_project_path
            if dependency_project.project_type == constants.TYPE_PROJECT_MODULE:
                docker_dir_with_addons = str(pathlib.PurePosixPath(docker_dir_with_addons, os.pardir))
            if list_of_subprojects:
                self.config.catalogs_of_modules_data.extend(list_of_subprojects)
                for subproject in list_of_subprojects:
                    self.config.docker_dirs_with_addons.append(str(pathlib.PurePosixPath(docker_dir_with_addons, subproject.subproject_rel_path)))
            else:
                self.config.docker_dirs_with_addons.append(docker_dir_with_addons)
            self.mapped_folders.append(
                MappedPath(local=dependency_project.project_path, docker=docker_dependency_project_path)
            )
        for pre_commit_file in self.config.pre_commit_map_files:
            real_file_place = os.path.join(self.config.developing_project_dir_path, pre_commit_file)
            if os.path.exists(real_file_place):
                full_path_pre_commit_file = os.path.join(self.config.project_dir,pre_commit_file)
                if not os.path.exists(full_path_pre_commit_file):
                    shutil.copy(real_file_place, full_path_pre_commit_file)
                self.mapped_folders.append(MappedPath(
                    local=full_path_pre_commit_file, 
                    docker=str(pathlib.PurePosixPath(self.config.docker_odoo_project_dir_path,pre_commit_file)),
                ))
            else:
                
                _logger.warning(translations.get_translation(translations.PRE_COMMIT_FILE_WAS_NOT_FOUND).format(
                    PRE_COMMIT_FILE=pre_commit_file,
                    ODOO_PROJECT_DIR_PATH=self.config.developing_project_dir_path,
                ))

    def generate_dockerfile(self) -> None:
        with open(self.config.project_dockerfile_template_path) as f:
            lines = f.readlines()
        content = "".join(lines).format(
            PROCESSOR_ARCH=self.config.arch,
            CURRENT_USER_UID=constants.CURRENT_USER_UID,
            CURRENT_USER_GID=constants.CURRENT_USER_GID,
            CURRENT_USER=constants.CURRENT_USER,
            CURRENT_PASSWORD=constants.CURRENT_PASSWORD,
            PYTHON_VERSION=self.config.python_version,
            DISTRO_NAME=self.config.distro_name,
            DISTRO_VERSION=self.config.distro_version, 
            DISTRO_VERSION_CODENAME=self.config.distro_version_codename,
        )
        content = content.replace(translations.get_translation(translations.MESSAGE_FOR_TEMPLATES), translations.get_translation(translations.DO_NOT_CHANGE_FILE))
        dockerfile_path = os.path.join(self.config.project_dir, constants.DOCKERFILE)
        self.config.dockerfile_path = dockerfile_path
        with open(dockerfile_path, 'w') as writer:
            writer.write(content)
    
    def check_oca_dependencies(self, project: HandleOdooProjectLink) -> None:
        self.checkout_project(project)
        oca_dependencies_txt = os.path.join(project.project_path, "oca_dependencies.txt")
        if os.path.exists(oca_dependencies_txt):
            with open(oca_dependencies_txt, "r") as oca_deps:
                oca_deps_content_lines = oca_deps.readlines()
            for oca_dep_string in oca_deps_content_lines:
                oca_dep_string = oca_dep_string.strip()
                if "#" in oca_dep_string:
                    continue
                if not "github" in oca_dep_string:
                    oca_dep_string = f"https://github.com/OCA/{oca_dep_string}.git"
                if oca_dep_string not in self.config.dependencies:
                    self.config.dependencies.append(oca_dep_string)
    
    def generate_config_file(self) -> None:
        config_file_template_path = os.path.join(self.config.project_dir, constants.PROJECT_ODOO_TEMPLATE_CONFIG_FILE_RELATIVE_PATH)
        with open(config_file_template_path) as f:
            lines = f.readlines()
        content = "".join(lines)
        for replace_phrase in {
                constants.DO_NOT_CHANGE_PARAM: translations.get_translation(translations.DO_NOT_CHANGE_PARAM),
                constants.ADMIN_PASSWD_MESSAGE: translations.get_translation(translations.ADMIN_PASSWD_MESSAGE),
                constants.MESSAGE_MARKER: translations.get_translation(translations.MESSAGE_FOR_TEMPLATES),
                constants.POSTGRES_ODOO_USER_MARKER: constants.POSTGRES_ODOO_USER,
                constants.POSTGRES_ODOO_PASS_MARKER: constants.POSTGRES_ODOO_PASS,
                constants.POSTGRES_ODOO_HOST_MARKER: constants.POSTGRES_ODOO_HOST,
                constants.POSTGRES_ODOO_PORT_MARKER: str(constants.POSTGRES_ODOO_PORT),
                constants.ODOO_PORT_MARKER: str(constants.ODOO_DOCKER_PORT),
            }.items():
            content = content.replace(replace_phrase[0], replace_phrase[1])
        if not os.path.exists(self.config.path_odoo_conf) or self.config.pd_manager.check_project_odoo_config_template(config_file_template_path):
            with open(self.config.path_odoo_conf, 'w') as writer:
                writer.write(content)
    
    def generate_docker_compose_file(self) -> None:
        docker_compose_template_path = os.path.join(self.config.project_dir, constants.PROJECT_DOCKER_COMPOSE_TEMPLATE_FILE_RELATIVE_PATH)
        with open(docker_compose_template_path) as f:
            lines = f.readlines()
        
        mapped_volumes = "\n"
        for mapped_volume in self.mapped_folders:
            mapped_volumes += " " * 6 + f"- {mapped_volume.local}:{mapped_volume.docker}:Z\n"
            if not os.path.exists(mapped_volume.local):
                path = Path(mapped_volume.local)
                path.mkdir(parents=True)

        content = "".join(lines).format(
            ODOO_IMAGE=self.config.odoo_image_name,
            MAPPED_VOLUMES=mapped_volumes,
            DEBUGGER_PORT=self.user_env.debugger_port or constants.DEBUGGER_DEFAULT_PORT,
            ODOO_PORT=self.user_env.odoo_port or constants.ODOO_DEFAULT_PORT,
            POSTGRES_PORT=self.user_env.postgres_port or constants.POSTGRES_DEFAULT_PORT,
            START_STRING=self.config.start_string,
            CURRENT_USER=constants.CURRENT_USER,
            CURRENT_PASSWORD=constants.CURRENT_PASSWORD,
            POSTGRES_ODOO_USER=constants.POSTGRES_ODOO_USER,
            POSTGRES_ODOO_PASS=constants.POSTGRES_ODOO_PASS,
            ODOO_DOCKER_PORT=constants.ODOO_DOCKER_PORT,
            DEBUGGER_DOCKER_PORT=constants.DEBUGGER_DOCKER_PORT,
            POSTGRES_DOCKER_PORT=constants.POSTGRES_DOCKER_PORT,
            COMPOSE_FILE_VERSION=self.config.compose_file_version,
            DATABASE_NAME_INSTANCE=constants.DATABASE_NAME_INSTANCE,
            POSTGRES_VERSION=self.config.postgres_version,
        )
        content = content.replace(translations.get_translation(translations.MESSAGE_FOR_TEMPLATES), translations.get_translation(translations.DO_NOT_CHANGE_FILE))
        dockerfile_compose_path = os.path.join(self.config.project_dir, "docker-compose.yml")
        with open(dockerfile_compose_path, 'w') as writer:
            writer.write(content)
    
    def checkout_dependencies(self) -> None:
        odoo_project = HandleOdooProjectLink(
            f"""file://{self.user_env.odoo_src_dir}""",
            self.user_env.path_to_ssh_key,
            self.user_env.odoo_projects_dir,
        )
        list_for_checkout = [odoo_project]
        list_for_checkout.extend(self.config.dependencies_projects)
        for project in list_for_checkout:
            self.checkout_project(project)

    def checkout_project(self, project: HandleOdooProjectLink) -> None:
        os.chdir(project.project_path)
        if not project.branch:
            project.branch = self.config.odoo_version
        current_branch_bytes = subprocess.run(["git", "branch", "--show-current"], capture_output=True)
        current_branch_string = current_branch_bytes.stdout.decode("utf-8").strip()
        try:
            current_branch_float = float(current_branch_string)
        except:
            current_branch_float = 0.0
        if current_branch_float and not project.is_developing and current_branch_string != project.branch:
            self.check_odoo_version_branch(project)
        if self.config.clean_git_repos:
            subprocess.run(["git", "stash"], capture_output=True)
            subprocess.run(["git", "checkout", self.config.odoo_version], capture_output=True)
        if self.config.update_git_repos:
            subprocess.run(["git", "pull"], capture_output=True)

    
    def check_odoo_version_branch(self, project: HandleOdooProjectLink) -> None:
        os.chdir(project.project_path)
        subprocess.run(["git", "stash"], capture_output=True)
        branch_commit_bytes = subprocess.run(["git", "rev-parse", "--verify", self.config.odoo_version], capture_output=True)
        branch_commit_string = branch_commit_bytes.stdout.decode("utf-8").strip()
        if "fatal" in branch_commit_string:
            newest_version = self.get_odoo_latest_version(os.chdir(project.project_path))
            subprocess.run(["git", "checkout", str(newest_version)])
            subprocess.run(["git", "pull"])
            newest_version = self.get_odoo_latest_version(os.chdir(project.project_path))
            if str(newest_version) == self.config.odoo_version:
                subprocess.run(["git", "checkout", str(newest_version)])
            else:
                _logger.error(f"Version {self.config.odoo_version} not exists in git repository {project.project_path}")
                exit(1)
        else:
            if project.branch and project.commit:
                subprocess.run(["git", "checkout", project.branch, project.commit], capture_output=True)
            else:
                subprocess.run(["git", "checkout", project.branch], capture_output=True)
    
    def get_odoo_latest_version(self, source_dir) -> float:
        os.chdir(source_dir)
        all_remote_branches_bytes = subprocess.run(["git", "branch", "-r", ], capture_output=True)
        all_remote_branches_string = all_remote_branches_bytes.stdout.decode("utf-8").strip()
        list_of_versions = []
        all_branches_list = all_remote_branches_string.split("\n")
        for branch_name in all_branches_list:
            try:
                branch_version = float(branch_name)
                list_of_versions.append(branch_version)
            except:
                continue
        newest_version = sorted(list_of_versions)[-1]
        return newest_version

    
    def update_links(self) -> None:
        def delete_old_links(dir_to_clean, current_links):
            os.chdir(dir_to_clean)
            for item in os.listdir():
                if os.path.islink(item) and not item in current_links:
                    os.unlink(item)
        
        def create_new_links(dir_to_create, current_links):
            for dep_for_link in current_links:
                dep_dir_name = os.path.basename(dep_for_link)
                try:
                    os.symlink(dep_for_link, os.path.join(dir_to_create, dep_dir_name))
                except FileExistsError:
                    pass
        if not os.path.exists(self.config.dependencies_dir) and self.config.dependencies_dirs:
            os.mkdir(self.config.dependencies_dir)
        delete_old_links(self.config.project_dir, self.config.list_for_symlinks)
        create_new_links(self.config.project_dir, self.config.list_for_symlinks)
        if self.config.dependencies_dirs:
            delete_old_links(self.config.dependencies_dir, self.config.dependencies_dirs)
            create_new_links(self.config.dependencies_dir, self.config.dependencies_dirs)
        list_of_all_modules = []
        for catalog_of_modules in self.config.catalogs_of_modules_data:
            list_of_all_modules.extend(catalog_of_modules.list_of_modules)
        
        if list_of_all_modules:
            odoo_src_addons_dir = os.path.join(self.user_env.odoo_src_dir, "odoo","addons")
            delete_old_links(odoo_src_addons_dir, list_of_all_modules)
            if self.config.create_module_links:
                create_new_links(odoo_src_addons_dir, list_of_all_modules)
    
    def generate_vscode_settings_json(self) -> None:
        vscode_settings_json_template_path = os.path.join(self.config.project_dir, constants.PROJECT_VSCODE_SETTINGS_TEMPLATE)
        with open(vscode_settings_json_template_path) as f:
            lines = f.readlines()
        content = "".join(lines[1:]).replace(
            "{PYTHON_VERSION}", self.config.python_version,
        )
        content = content.replace(translations.get_translation(translations.MESSAGE_FOR_TEMPLATES), translations.get_translation(translations.DO_NOT_CHANGE_FILE))
        vscode_settings_json_path = os.path.join(self.get_vscode_dir_path(), "settings.json")
        with open(vscode_settings_json_path, 'w') as writer:
            writer.write(content)
    
    def get_vscode_dir_path(self) -> str:
        vscode_dir = os.path.join(self.config.project_dir, ".vscode")
        if not os.path.exists(vscode_dir):
            os.mkdir(vscode_dir)
        return vscode_dir

    
    def update_vscode_debugger_launcher(self) -> None:

        def get_list_of_mapped_sources() -> None:
            list_for_links = [
                self.user_env.odoo_src_dir,
                self.config.developing_project_dir_path,
            ]
            for linking_dir in list_for_links:
                dir_name_to_link = os.path.basename(linking_dir)
                for mapped_folder in self.mapped_folders:
                    mapped_dir_name = os.path.basename(mapped_folder.docker)
                    if dir_name_to_link == mapped_dir_name:
                        self.config.debugger_path_mappings.append(DebuggerPathRecord(
                            localRoot=os.path.join(self.config.project_dir, dir_name_to_link), 
                            remoteRoot=mapped_folder.docker,
                        ))
            for linking_dir in self.config.dependencies_dirs:
                dir_name_to_link = os.path.basename(linking_dir)
                for mapped_folder in self.mapped_folders:
                    mapped_dir_name = os.path.basename(mapped_folder.docker)
                    if dir_name_to_link == mapped_dir_name:
                        self.config.debugger_path_mappings.append(DebuggerPathRecord(
                            localRoot=os.path.join(self.config.dependencies_dir, dir_name_to_link), 
                            remoteRoot=mapped_folder.docker,
                        ))

        launch_json = os.path.join(self.get_vscode_dir_path(), "launch.json")
        if not os.path.exists(launch_json):
            content = {
                "configurations": []
            }
        else:
            with open(launch_json, "r") as open_file:
                content = json.load(open_file)
        debugger_unit_exists = False
        get_list_of_mapped_sources()
        port = self.user_env.debugger_port or constants.DEBUGGER_DEFAULT_PORT
        odoo_debugger_uint = DebuggerUnit(
            name=constants.DEBUGGER_UNIT_NAME,
            type="python",
            request="attach",
            port=int(port),
            host="localhost",
            pathMappings=self.config.debugger_path_mappings,
        )
        for index, debugger_unit in enumerate(content["configurations"]):
            if debugger_unit["name"] == constants.DEBUGGER_UNIT_NAME:
                content["configurations"][index] = odoo_debugger_uint
                debugger_unit_exists = True
        if not debugger_unit_exists:
            content["configurations"].append(DebuggerUnit(
                name=constants.DEBUGGER_UNIT_NAME,
                type="python",
                request="attach",
                port=self.user_env.debugger_port or constants.DEBUGGER_DEFAULT_PORT,
                host="localhost",
                pathMappings=self.config.debugger_path_mappings,
            ))
        with open(launch_json, "w") as outfile:
            json.dump(content, outfile, indent=4)
    
    def clone_odoo(self):
        dir_for_odoo_src = os.path.join(self.user_env.odoo_src_dir, "..")
        os.chdir(dir_for_odoo_src)
        if not self.config.user_env.path_to_ssh_key:
            subprocess.run(["git", "clone", constants.ODOO_GIT_LINK])
        else:
            subprocess.call(f'git clone {constants.ODOO_GIT_LINK} --config core.sshCommand="ssh -i {self.config.user_env.path_to_ssh_key}"', shell=True)
    
    def download_odoo_repository(self):
        self.config.system_checker.check_free_space_for_odoo_developing()
        dir_for_odoo_src = os.path.join(self.user_env.odoo_src_dir, "..")
        os.chdir(dir_for_odoo_src)
        delete_files_in_directory(self.user_env.odoo_src_dir)
        link_to_download = get_direct_link_to_download_from_yadisk(constants.YADISK_SHARING_LINK)
        filepath_to_save = os.path.join(Path.home(), "odoo.zip.download")
        download_file(link_to_download=link_to_download, filepath_to_save=filepath_to_save)
        un_zip_file_to_directory(dir_for_odoo_src, filepath_to_save)
        os.chdir(self.user_env.odoo_src_dir)
        subprocess.run(["git", "pull"])
        if os.path.exists(filepath_to_save):
            os.remove(filepath_to_save)
    
    def build_image(self):
        os.chdir(self.config.project_dir)
        # TODO i need to create .dockerignore file (because it tries to send docker context)
        subprocess.run(["docker", "build", "-f", self.config.dockerfile_path, "-t", self.config.odoo_image_name, f"--platform=linux/{self.config.arch}", self.config.project_dir])