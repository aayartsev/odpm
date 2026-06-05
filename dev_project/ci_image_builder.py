from __future__ import annotations

import os
import pathlib
import shutil
from typing import TYPE_CHECKING

from . import constants, translations
from .bake_venv import VenvInstallSpec, get_venv_bootstrap_packages, write_ci_bake_dir
from .errors import PipelineError
from .inside_docker_app.logger import get_module_logger
from .inside_docker_app.utils import write_odoo_config_data_to_file
from .project_env_types import MappedPath
from .subprocess_runner import run_logged

if TYPE_CHECKING:
    from .host_project_env import CreateProjectEnvironment

_logger = get_module_logger(__name__)


class CiImageBuilder:
    def __init__(self, env: CreateProjectEnvironment) -> None:
        self.env = env

    @property
    def config(self):
        return self.env.config

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

    def _read_ci_dockerignore_template(self) -> str:
        template_path = os.path.join(
            self.config.program_dir,
            constants.PROGRAM_CI_DOCKERIGNORE_TEMPLATE_FILE_RELATIVE_PATH,
        )
        with open(template_path) as reader:
            return reader.read()

    def prepare_ci_build_context(self) -> None:
        context_dir = self.config.ci_build_context_dir
        if os.path.exists(context_dir):
            shutil.rmtree(context_dir)
        os.makedirs(context_dir)

        copied = 0
        for mapped in self.env.mapped_folders:
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
        dockerignore_path = os.path.join(context_dir, constants.DOCKERIGNORE)
        with open(dockerignore_path, "w") as writer:
            writer.write(self._read_ci_dockerignore_template())

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
        self.env._base_image.ensure_base_image()
        self.prepare_ci_build_context()
        ci_dockerfile = self.generate_ci_dockerfile()
        context_dir = self.config.ci_build_context_dir
        _logger.info(
            "build_ci_image: building %s from %s (base %s)",
            self.config.odoo_ci_image_name,
            ci_dockerfile,
            self.config.odoo_image_name,
        )
        returncode = run_logged(
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
        if returncode != 0:
            message = translations.get_translation(
                translations.DOCKER_BUILD_FAILED
            ).format(EXIT_CODE=returncode)
            _logger.error(message)
            raise PipelineError(message, exit_code=returncode)
        _logger.info(
            "build_ci_image: finished %s", self.config.odoo_ci_image_name
        )
