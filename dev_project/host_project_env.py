import json
import os
import pathlib
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Literal, NamedTuple, TypedDict

from . import constants, translations
from .handle_odoo_project_git_link import HandleOdooProjectLink
from .host_config import Config
from .inside_docker_app.logger import get_module_logger
from .bake_venv import VenvInstallSpec, get_venv_bootstrap_packages, write_ci_bake_dir
from .inside_docker_app.utils import (
    delete_files_in_directory,
    download_file,
    un_zip_file_to_directory,
    write_odoo_config_data_to_file,
)
from .dependency_resolver import read_oca_dependency_urls, resolve_dependency_urls
from .protocols import CreateProjectEnvironmentProtocol
from .scenario_policy import ScenarioPolicy

_logger = get_module_logger(__name__)
_ = translations._


class MappedPath(NamedTuple):
    local: str
    docker: str


class MappedSources(NamedTuple):
    local: str
    remote: str


class SymlinksSources(NamedTuple):
    source_path: str
    link_path: str


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
        self.odoo_platform_project: HandleOdooProjectLink

    def map_folders(self) -> None:
        self.mapped_folders = [
            MappedPath(
                local=self.config.odoo_src_dir, docker=self.config.docker_odoo_dir
            ),
            MappedPath(local=self.config.venv_dir, docker=self.config.docker_venv_dir),
            MappedPath(
                local=self.config.odoo_tests_dir,
                docker=self.config.docker_temp_tests_dir,
            ),
            MappedPath(
                local=os.path.join(self.config.program_dir, constants.DEV_PROJECT_DIR),
                docker=self.config.docker_dev_project_dir,
            ),
            MappedPath(
                local=self.user_env.backups, docker=self.config.docker_backups_dir
            ),
            MappedPath(
                local=os.path.join(self.config.dir_for_odoo_container_home, ".local"),
                docker=str(
                    pathlib.PurePosixPath(self.config.docker_project_dir, ".local")
                ),
            ),
            MappedPath(
                local=os.path.join(self.config.dir_for_odoo_container_home, ".cache"),
                docker=str(
                    pathlib.PurePosixPath(self.config.docker_project_dir, ".cache")
                ),
            ),
        ]
        if self.config.developing_project.project_path:
            self.mapped_folders.append(
                MappedPath(
                    local=self.config.developing_project.project_path,
                    docker=self.config.docker_odoo_project_dir_path,
                ),
            )
        resolved_dependencies = self._resolve_dependencies()
        self.config.dependencies = resolved_dependencies
        for dependency_string in resolved_dependencies:
            dependency_project = self.config.handle_git_link(dependency_string)
            if not dependency_project.is_cloned:
                continue
            list_of_subprojects = self.config.check_project_for_subprojects(
                dependency_project.project_path
            )
            docker_dependency_project_path = str(
                pathlib.PurePosixPath(
                    self.config.docker_extra_addons,
                    dependency_project.inside_docker_path,
                )
            )
            self.config.dependencies_projects.append(dependency_project)
            self.config.dependencies_dirs.append(dependency_project.project_path)
            docker_dir_with_addons = docker_dependency_project_path
            if (
                dependency_project.project_data.project_type
                == constants.TYPE_PROJECT_MODULE
            ):
                docker_dir_with_addons = str(
                    pathlib.PurePosixPath(docker_dir_with_addons, os.pardir)
                )
            if list_of_subprojects:
                self.config.catalogs_of_modules_data.extend(list_of_subprojects)
                for subproject in list_of_subprojects:
                    self.config.docker_dirs_with_addons.append(
                        str(
                            pathlib.PurePosixPath(
                                docker_dir_with_addons, subproject.subproject_rel_path
                            )
                        )
                    )
            else:
                self.config.docker_dirs_with_addons.append(docker_dir_with_addons)
            self.mapped_folders.append(
                MappedPath(
                    local=dependency_project.project_path,
                    docker=docker_dependency_project_path,
                )
            )
        for pre_commit_file in self.config.pre_commit_map_files:
            real_file_place = os.path.join(
                self.config.developing_project_dir_path, pre_commit_file
            )
            if os.path.exists(real_file_place):
                full_path_pre_commit_file = os.path.join(
                    self.config.project_dir, pre_commit_file
                )
                if not os.path.exists(full_path_pre_commit_file):
                    shutil.copy(real_file_place, full_path_pre_commit_file)
                self.mapped_folders.append(
                    MappedPath(
                        local=full_path_pre_commit_file,
                        docker=str(
                            pathlib.PurePosixPath(
                                self.config.docker_odoo_project_dir_path,
                                pre_commit_file,
                            )
                        ),
                    )
                )
            else:
                _logger.warning(
                    translations.get_translation(
                        translations.PRE_COMMIT_FILE_WAS_NOT_FOUND
                    ).format(
                        PRE_COMMIT_FILE=pre_commit_file,
                        ODOO_PROJECT_DIR_PATH=self.config.developing_project_dir_path,
                    )
                )

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
        content = content.replace(
            translations.get_translation(translations.MESSAGE_FOR_TEMPLATES),
            translations.get_translation(translations.DO_NOT_CHANGE_FILE),
        )
        dockerfile_path = os.path.join(self.config.project_dir, constants.DOCKERFILE)
        self.config.dockerfile_path = dockerfile_path
        with open(dockerfile_path, "w") as writer:
            writer.write(content)

    def _get_oca_urls_for_dependency(self, dependency_string: str) -> list[str]:
        project = self.config.handle_git_link(dependency_string)
        if not project.is_cloned:
            _logger.warning(
                translations.get_translation(
                    translations.OCA_DEPENDENCY_NOT_CLONED
                ).format(DEPENDENCY_URL=dependency_string)
            )
            return []
        self.checkout_project(project)
        return read_oca_dependency_urls(project.project_path)

    def _resolve_dependencies(self) -> list[str]:
        seed_urls = list(self.config.dependencies)
        if not self.config.use_oca_dependencies:
            return seed_urls

        initial_extra_urls: list[str] = []
        if self.config.developing_project.project_path:
            self.checkout_project(self.config.developing_project)
            initial_extra_urls = read_oca_dependency_urls(
                self.config.developing_project.project_path
            )

        return resolve_dependency_urls(
            seed_urls,
            self._get_oca_urls_for_dependency,
            initial_extra_urls=initial_extra_urls,
        )

    def generate_config_file(self) -> None:
        config_file_template_path = os.path.join(
            self.config.project_dir,
            constants.PROJECT_ODOO_TEMPLATE_CONFIG_FILE_RELATIVE_PATH,
        )
        with open(config_file_template_path) as f:
            lines = f.readlines()
        content = "".join(lines)
        for replace_phrase in {
            constants.DO_NOT_CHANGE_PARAM: translations.get_translation(
                translations.DO_NOT_CHANGE_PARAM
            ),
            constants.ADMIN_PASSWD_MESSAGE: translations.get_translation(
                translations.ADMIN_PASSWD_MESSAGE
            ),
            constants.MESSAGE_MARKER: translations.get_translation(
                translations.MESSAGE_FOR_TEMPLATES
            ),
            constants.POSTGRES_ODOO_USER_MARKER: constants.POSTGRES_ODOO_USER,
            constants.POSTGRES_ODOO_PASS_MARKER: constants.POSTGRES_ODOO_PASS,
            constants.POSTGRES_ODOO_HOST_MARKER: constants.POSTGRES_ODOO_HOST,
            constants.POSTGRES_ODOO_PORT_MARKER: str(constants.POSTGRES_ODOO_PORT),
            constants.ODOO_PORT_MARKER: str(constants.ODOO_DOCKER_PORT),
        }.items():
            content = content.replace(replace_phrase[0], replace_phrase[1])
        if not os.path.exists(
            self.config.path_odoo_conf
        ) or self.config.pd_manager.check_project_odoo_config_template(
            config_file_template_path
        ):
            with open(self.config.path_odoo_conf, "w") as writer:
                writer.write(content)

    def _ensure_compose_template_current(self, template_path: str) -> list[str]:
        with open(template_path) as template_file:
            lines = template_file.readlines()
        if "{DEV_EXTRA_PORTS}" in "".join(lines):
            return lines
        _logger.info(
            "Upgrading %s to scenario-aware docker-compose template",
            template_path,
        )
        self.config.pd_manager.rebuild_docker_compose_template()
        with open(template_path) as template_file:
            return template_file.readlines()

    def generate_docker_compose_file(self) -> None:
        docker_compose_template_path = os.path.join(
            self.config.project_dir,
            constants.PROJECT_DOCKER_COMPOSE_TEMPLATE_FILE_RELATIVE_PATH,
        )
        lines = self._ensure_compose_template_current(docker_compose_template_path)

        mapped_volumes = "\n"
        for mapped_volume in self.mapped_folders:
            mapped_volumes += (
                " " * 6 + f"- {mapped_volume.local}:{mapped_volume.docker}:Z\n"
            )
            if not os.path.exists(mapped_volume.local):
                path = Path(mapped_volume.local)
                path.mkdir(parents=True)

        policy = ScenarioPolicy.from_scenario(self.config.user_env.odpm_scenario)
        odoo_image = getattr(self.config, policy.odoo_image_attr)

        POSTGRES_PORT = self.user_env.postgres_port or constants.POSTGRES_DEFAULT_PORT
        POSTGRES_PORT_MAP = policy.build_postgres_port_map(
            f"{POSTGRES_PORT}:{constants.POSTGRES_DOCKER_PORT}"
        )
        DEBUGGER_PORT = self.user_env.debugger_port or constants.DEBUGGER_DEFAULT_PORT
        DEBUGGER_PORT_MAP = (
            f"{DEBUGGER_PORT}:{constants.DEBUGGER_DOCKER_PORT}"
        )
        DEV_EXTRA_PORTS = policy.build_dev_extra_ports(DEBUGGER_PORT_MAP)
        ODOO_VOLUMES_BLOCK = policy.build_odoo_volumes_block(mapped_volumes)

        legacy_mapped_volumes = (
            mapped_volumes if policy.include_odoo_volumes else "\n"
        )
        content = "".join(lines).format(
            ODOO_IMAGE=odoo_image,
            DEV_EXTRA_PORTS=DEV_EXTRA_PORTS,
            ODOO_VOLUMES_BLOCK=ODOO_VOLUMES_BLOCK,
            ODOO_PORT=self.user_env.odoo_port or constants.ODOO_DEFAULT_PORT,
            POSTGRES_PORT_MAP=POSTGRES_PORT_MAP,
            GEVENT_PORT=self.user_env.gevent_port or constants.GEVENT_DEFAULT_PORT,
            START_STRING=self.config.start_string,
            CURRENT_USER=constants.CURRENT_USER,
            CURRENT_PASSWORD=constants.CURRENT_PASSWORD,
            POSTGRES_ODOO_USER=constants.POSTGRES_ODOO_USER,
            POSTGRES_ODOO_PASS=constants.POSTGRES_ODOO_PASS,
            ODOO_DOCKER_PORT=constants.ODOO_DOCKER_PORT,
            DEBUGGER_DOCKER_PORT=constants.DEBUGGER_DOCKER_PORT,
            GEVENT_DOCKER_PORT=constants.GEVENT_DOCKER_PORT,
            COMPOSE_FILE_VERSION=self.config.compose_file_version,
            DATABASE_NAME_INSTANCE=constants.DATABASE_NAME_INSTANCE,
            POSTGRES_VERSION=self.config.postgres_version,
            POSTGRES_DATA_LOCAL_STORAGE=self.config.postgres_data_local_storage,
            # Legacy placeholders ( prefer auto-upgrade above)
            DEBUGGER_PORT_MAP=DEBUGGER_PORT_MAP,
            MAPPED_VOLUMES=legacy_mapped_volumes,
        )
        content = content.replace(
            constants.MESSAGE_MARKER,
            translations.get_translation(translations.DO_NOT_CHANGE_FILE),
        )
        dockerfile_compose_path = os.path.join(
            self.config.project_dir, "docker-compose.yml"
        )
        with open(dockerfile_compose_path, "w") as writer:
            writer.write(content)

    def checkout_dependencies(self) -> None:
        list_for_checkout = [self.config.odoo_platform_project]
        list_for_checkout.extend(self.config.dependencies_projects)
        for project in list_for_checkout:
            self.checkout_project(project)

    def checkout_project(self, project: HandleOdooProjectLink) -> None:
        project.checkout_repository(
            self.config.odoo_version,
            clean_git_repos=self.config.clean_git_repos,
            update_git_repos=self.config.update_git_repos,
        )

    def update_links(self) -> None:

        def delete_old_links(dir_to_clean, current_links):
            os.chdir(dir_to_clean)
            for item in os.listdir():
                if os.path.islink(item) and item not in current_links:
                    os.unlink(item)

        def create_new_links(dir_to_create, current_links):
            for dep_for_link in current_links:
                dep_dir_name = os.path.basename(dep_for_link)
                try:
                    os.symlink(dep_for_link, os.path.join(dir_to_create, dep_dir_name))
                    self.config.symlinks_sources.append(
                        SymlinksSources(
                            source_path=dep_for_link,
                            link_path=os.path.join(
                                dep_for_link, os.path.join(dir_to_create, dep_dir_name)
                            ),
                        )
                    )
                except FileExistsError:
                    pass

        if (
            not os.path.exists(self.config.dependencies_dir)
            and self.config.dependencies_dirs
        ):
            os.mkdir(self.config.dependencies_dir)
        delete_old_links(self.config.project_dir, self.config.list_for_symlinks)
        create_new_links(self.config.project_dir, self.config.list_for_symlinks)
        if self.config.dependencies_dirs:
            delete_old_links(
                self.config.dependencies_dir, self.config.dependencies_dirs
            )
            create_new_links(
                self.config.dependencies_dir, self.config.dependencies_dirs
            )
        list_of_all_modules = []
        for catalog_of_modules in self.config.catalogs_of_modules_data:
            list_of_all_modules.extend(catalog_of_modules.list_of_modules)

        if list_of_all_modules:
            odoo_src_addons_dir = os.path.join(
                self.config.odoo_src_dir, self.config.platform_name, "addons"
            )
            delete_old_links(odoo_src_addons_dir, list_of_all_modules)
            if self.config.create_module_links:
                create_new_links(odoo_src_addons_dir, list_of_all_modules)

    def generate_vscode_settings_json(self) -> None:
        vscode_settings_json_template_path = os.path.join(
            self.config.project_dir, constants.PROJECT_VSCODE_SETTINGS_TEMPLATE
        )
        with open(vscode_settings_json_template_path) as f:
            lines = f.readlines()
        content = "".join(lines[1:]).replace(
            "{PYTHON_VERSION}",
            self.config.python_version,
        )
        content = content.replace(
            translations.get_translation(translations.MESSAGE_FOR_TEMPLATES),
            translations.get_translation(translations.DO_NOT_CHANGE_FILE),
        )
        vscode_settings_json_path = os.path.join(
            self.get_vscode_dir_path(), "settings.json"
        )
        with open(vscode_settings_json_path, "w") as writer:
            writer.write(content)

    def get_vscode_dir_path(self) -> str:
        vscode_dir = os.path.join(self.config.project_dir, ".vscode")
        if not os.path.exists(vscode_dir):
            os.mkdir(vscode_dir)
        return vscode_dir

    def update_vscode_debugger_launcher(self) -> None:
        def get_list_of_mapped_sources() -> None:
            list_for_links = [
                symlink_item for symlink_item in self.config.symlinks_sources
            ]
            for linking_dir in list_for_links:
                dir_name_to_link = os.path.basename(linking_dir.link_path)
                for mapped_folder in self.mapped_folders:
                    mapped_dir_name = os.path.basename(mapped_folder.local)
                    if (
                        dir_name_to_link == mapped_dir_name
                        and linking_dir.source_path not in [self.user_env.backups]
                    ):
                        self.config.debugger_path_mappings.append(
                            DebuggerPathRecord(
                                localRoot=linking_dir.link_path,
                                remoteRoot=mapped_folder.docker,
                            )
                        )

        launch_json = os.path.join(self.get_vscode_dir_path(), "launch.json")
        if not os.path.exists(launch_json):
            content = {"configurations": []}
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
            content["configurations"].append(
                DebuggerUnit(
                    name=constants.DEBUGGER_UNIT_NAME,
                    type="python",
                    request="attach",
                    port=self.user_env.debugger_port or constants.DEBUGGER_DEFAULT_PORT,
                    host="localhost",
                    pathMappings=self.config.debugger_path_mappings,
                )
            )
        with open(launch_json, "w") as outfile:
            json.dump(content, outfile, indent=4)

    def download_odoo_repository(self):
        self.config.system_checker.check_free_space_for_odoo_developing()
        dir_for_odoo_src = os.path.join(self.config.odoo_src_dir, "..")
        os.chdir(dir_for_odoo_src)
        delete_files_in_directory(self.config.odoo_src_dir)
        subprocess.run(["git", "clone", "--depth", "1", constants.ODOO_GIT_LINK])

    def download_odoo_nightly_build(self):
        self.config.system_checker.check_free_space_for_odoo_developing(
            free_space_size=2.0
        )
        dir_for_odoo_src = os.path.join(self.config.odoo_src_dir, "..")
        os.chdir(dir_for_odoo_src)
        delete_files_in_directory(self.config.odoo_src_dir)
        odoo_version = self.config.odoo_version
        odoo_build_date = (
            self.config.odoo_build_date or constants.ODOO_DEFAULT_BUILD_DATE
        )
        link_to_download = f"https://nightly.odoo.com/{odoo_version}/nightly/src/odoo_{odoo_version}.{odoo_build_date}.zip"
        filepath_to_save = os.path.join(Path.home(), "odoo.zip.download")
        download_file(
            link_to_download=link_to_download,
            filepath_to_save=filepath_to_save,
        )
        un_zip_file_to_directory(
            dir_for_odoo_src,
            filepath_to_save,
            rename_first_part_of_path="odoo",
        )
        os.replace(
            os.path.join(self.config.odoo_src_dir, "setup", "odoo"),
            os.path.join(self.config.odoo_src_dir, "odoo-bin"),
        )
        if os.path.exists(filepath_to_save):
            os.remove(filepath_to_save)

    def base_image_exists(self) -> bool:
        process_result = subprocess.run(
            ["docker", "images", "--format", "'{{json .}}'"], capture_output=True
        )
        output_string = process_result.stdout.decode("utf-8")
        for record in output_string.split("\n"):
            if not record:
                continue
            new_record = json.loads(record.replace("'", ""))
            if self.config.odoo_image_name == new_record.get("Repository"):
                return True
        return False

    def ensure_base_image(self) -> None:
        if not self.base_image_exists():
            self.build_base_image()

    def _docker_path_to_context_rel(self, docker_path: str) -> str:
        docker_base = pathlib.PurePosixPath(self.config.docker_project_dir)
        return str(pathlib.PurePosixPath(docker_path).relative_to(docker_base))

    def _should_copy_for_ci_image(self, mapped: MappedPath) -> bool:
        if not os.path.isdir(mapped.local):
            return False
        docker_path = mapped.docker
        skip_exact = {
            self.config.docker_venv_dir,
            self.config.docker_dev_project_dir,
            self.config.docker_backups_dir,
            self.config.docker_temp_tests_dir,
            str(pathlib.PurePosixPath(self.config.docker_project_dir, ".local")),
            str(pathlib.PurePosixPath(self.config.docker_project_dir, ".cache")),
        }
        if docker_path in skip_exact:
            return False
        docker_odoo = self.config.docker_odoo_dir
        docker_extra = self.config.docker_extra_addons
        if docker_path == docker_odoo or docker_path.startswith(f"{docker_odoo}/"):
            return True
        if docker_path == docker_extra or docker_path.startswith(f"{docker_extra}/"):
            return True
        return False

    def _ci_copytree_ignore(self, _directory: str, names: list) -> set:
        return {name for name in names if name in (".git", "__pycache__")}

    def _build_ci_venv_install_spec(self) -> VenvInstallSpec:
        extra_packages = [
            package.strip()
            for package in self.config.requirements_txt
            if package and package.strip()
        ]
        lock_file_path = os.path.join(self.config.docker_venv_dir, ".lock")
        return VenvInstallSpec(
            project_dir=self.config.docker_project_dir,
            venv_dir=self.config.docker_venv_dir,
            odoo_requirements_path=os.path.join(
                self.config.docker_odoo_dir, "requirements.txt"
            ),
            extra_packages=extra_packages,
            python_version=self.config.python_version,
            bootstrap_packages=get_venv_bootstrap_packages(
                self.config.python_version
            ),
            lock_file_path=lock_file_path,
            lock_hash=self.config.compute_venv_lock_hash(),
        )

    def _prepare_ci_bake_files(self, context_dir: str) -> None:
        dev_project_dir = os.path.join(
            self.config.program_dir, constants.DEV_PROJECT_DIR
        )
        write_ci_bake_dir(
            context_dir,
            self._build_ci_venv_install_spec(),
            dev_project_dir,
        )

    def prepare_ci_build_context(self) -> None:
        context_dir = self.config.ci_build_context_dir
        if os.path.exists(context_dir):
            shutil.rmtree(context_dir)
        os.makedirs(context_dir)

        copied = 0
        for mapped in self.mapped_folders:
            if not self._should_copy_for_ci_image(mapped):
                continue
            rel_path = self._docker_path_to_context_rel(mapped.docker)
            dest_dir = os.path.join(context_dir, rel_path)
            parent_dir = os.path.dirname(dest_dir)
            if parent_dir:
                os.makedirs(parent_dir, exist_ok=True)
            shutil.copytree(
                mapped.local,
                dest_dir,
                dirs_exist_ok=True,
                ignore=self._ci_copytree_ignore,
            )
            copied += 1

        write_odoo_config_data_to_file(
            self.config.odoo_config_data,
            os.path.join(context_dir, constants.ODOO_CONF_NAME),
        )
        dockerignore_path = os.path.join(context_dir, ".dockerignore")
        with open(dockerignore_path, "w") as writer:
            writer.write(constants.CI_CONTEXT_DOCKERIGNORE)

        self._prepare_ci_bake_files(context_dir)

        bake_modules = ", ".join(
            os.path.basename(path) for path in constants.CI_BAKE_PYTHON_FILES
        )
        _logger.info(
            "prepare_ci_build_context: %s (%s source tree(s), %s, %s/[%s, %s])",
            context_dir,
            copied,
            constants.ODOO_CONF_NAME,
            constants.CI_BAKE_DIR,
            bake_modules,
            constants.CI_VENV_INSTALL_JSON,
        )

    def build_base_image(self) -> None:
        os.chdir(self.config.project_dir)
        # TODO i need to create .dockerignore file (because it tries to send docker context)
        subprocess.run(
            [
                "docker",
                "build",
                "-f",
                self.config.dockerfile_path,
                "-t",
                self.config.odoo_image_name,
                f"--platform=linux/{self.config.arch}",
                self.config.project_dir,
            ]
        )

    def generate_ci_dockerfile(self) -> str:
        template_path = os.path.join(
            self.config.program_dir, constants.CI_DOCKERFILE_TEMPLATE
        )
        with open(template_path) as template_file:
            content = template_file.read()
        content = content.format(
            BASE_IMAGE=self.config.odoo_image_name,
            DOCKER_PROJECT_DIR=self.config.docker_project_dir,
            CURRENT_USER=constants.CURRENT_USER,
            CI_BAKE_DIR=constants.CI_BAKE_DIR,
            CI_VENV_INSTALL_JSON=constants.CI_VENV_INSTALL_JSON,
        )
        content = content.replace(
            constants.MESSAGE_MARKER,
            translations.get_translation(translations.DO_NOT_CHANGE_FILE),
        )
        dockerfile_path = os.path.join(
            self.config.ci_build_context_dir, constants.CI_DOCKERFILE
        )
        with open(dockerfile_path, "w") as writer:
            writer.write(content)
        return dockerfile_path

    def build_ci_image(self) -> None:
        self.ensure_base_image()
        self.prepare_ci_build_context()
        ci_dockerfile = self.generate_ci_dockerfile()
        context_dir = self.config.ci_build_context_dir
        _logger.info(
            "build_ci_image: building %s from %s (base %s)",
            self.config.odoo_ci_image_name,
            ci_dockerfile,
            self.config.odoo_image_name,
        )
        result = subprocess.run(
            [
                "docker",
                "build",
                "-f",
                ci_dockerfile,
                "-t",
                self.config.odoo_ci_image_name,
                f"--platform=linux/{self.config.arch}",
                context_dir,
            ],
            cwd=self.config.project_dir,
        )
        if result.returncode != 0:
            _logger.error(
                "build_ci_image: docker build failed (exit %s)", result.returncode
            )
            sys.exit(result.returncode)
        _logger.info(
            "build_ci_image: finished %s", self.config.odoo_ci_image_name
        )
