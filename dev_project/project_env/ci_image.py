from __future__ import annotations

import os
import pathlib
import shutil
from typing import TYPE_CHECKING

from .. import constants
from ..translations import _
from ..bake_venv import (
    VenvInstallSpec,
    get_venv_bootstrap_packages,
    write_ci_venv_install_spec,
)
from ..config.payload import write_runtime_config_to_path
from ..logging import get_module_logger
from ..inside_docker_app.utils import write_odoo_config_data_to_file
from .base_image import BaseImageBuilder
from .types import MappedPath

if TYPE_CHECKING:
    from .environment import CreateProjectEnvironment
from .secrets import prepare_secrets_for_ci_bake, secrets_runtime_path


_logger = get_module_logger(__name__)


class CiImageBuilder:
    def __init__(self, env: CreateProjectEnvironment) -> None:
        self.env = env

    @property
    def config(self):
        return self.env.bootstrap.config

    def _docker_path_to_context_rel(self, docker_path: str) -> str:
        docker_base = pathlib.PurePosixPath(
            self.config.docker_layout.docker_project_dir
        )
        return str(pathlib.PurePosixPath(docker_path).relative_to(docker_base))

    def _should_copy_for_ci_image(self, mapped: MappedPath) -> bool:
        if not os.path.isdir(mapped.local):
            return False
        docker_path = mapped.docker
        skip_exact = {
            self.config.docker_layout.docker_venv_dir,
            self.config.docker_layout.docker_dev_project_dir,
            self.config.docker_layout.docker_backups_dir,
            self.config.docker_layout.docker_temp_tests_dir,
            str(pathlib.PurePosixPath(self.config.docker_layout.docker_project_dir, ".local")),
            str(pathlib.PurePosixPath(self.config.docker_layout.docker_project_dir, ".cache")),
        }
        if docker_path in skip_exact:
            return False
        docker_odoo = self.config.docker_layout.docker_odoo_dir
        docker_extra = self.config.docker_layout.docker_extra_addons
        if docker_path == docker_odoo or docker_path.startswith(f"{docker_odoo}/"):
            return True
        if docker_path == docker_extra or docker_path.startswith(f"{docker_extra}/"):
            return True
        return False

    def _ci_copytree_ignore(self, _directory: str, names: list) -> set:
        ignored = {name for name in names if name in (".git", "__pycache__")}
        ignored.update(name for name in names if name.endswith(".pyc"))
        return ignored

    def _ci_dev_project_copytree_ignore(self, _directory: str, names: list) -> set:
        ignored = self._ci_copytree_ignore(_directory, names)
        ignored.update(
            name for name in names if name in constants.CI_DEV_PROJECT_COPY_IGNORE_DIRS
        )
        ignored.update(name for name in names if name.endswith(".md"))
        return ignored

    def _copy_dev_project_for_ci(self, context_dir: str) -> None:
        dev_project_dir = os.path.join(
            self.config.program_dir, constants.DEV_PROJECT_DIR
        )
        rel_path = self._docker_path_to_context_rel(
            self.config.docker_layout.docker_dev_project_dir
        )
        dest_dir = os.path.join(context_dir, rel_path)
        parent_dir = os.path.dirname(dest_dir)
        if parent_dir:
            os.makedirs(parent_dir, exist_ok=True)
        shutil.copytree(
            dev_project_dir,
            dest_dir,
            dirs_exist_ok=True,
            ignore=self._ci_dev_project_copytree_ignore,
        )

    def _build_ci_venv_install_spec(self) -> VenvInstallSpec:
        extra_packages = [
            package.strip()
            for package in self.config.project_settings.requirements_txt
            if package and package.strip()
        ]
        lock_file_path = os.path.join(
            self.config.docker_layout.docker_venv_dir, ".lock"
        )
        return VenvInstallSpec(
            project_dir=self.config.docker_layout.docker_project_dir,
            venv_dir=self.config.docker_layout.docker_venv_dir,
            odoo_requirements_path=os.path.join(
                self.config.docker_layout.docker_odoo_dir, "requirements.txt"
            ),
            extra_packages=extra_packages,
            python_version=self.config.project_settings.python_version,
            bootstrap_packages=get_venv_bootstrap_packages(
                self.config.project_settings.python_version
            ),
            lock_file_path=lock_file_path,
            lock_hash=self.config.compute_venv_lock_hash(),
        )

    def _write_ci_venv_spec(self, context_dir: str) -> None:
        write_ci_venv_install_spec(
            context_dir,
            self._build_ci_venv_install_spec(),
        )

    def _write_ci_runtime_config(self, context_dir: str) -> None:
        config_path = os.path.join(
            context_dir, constants.CI_RUNTIME_CONFIG_CONTEXT_REL_PATH
        )
        write_runtime_config_to_path(self.config, config_path)

    def _ensure_odoo_config_data_for_bake(self) -> None:
        """Refresh secrets + manifest, then fill ``odoo_config_data`` for CI bake.

        ``odpm image … ensure`` skips ``template.odoo_conf``; without this step the
        runtime JSON would lack ``options`` (KeyError in ``wait_for_postgres``).
        """
        from ..config.config import Config
        from ..config.transforms.env_substitution import with_secrets
        from ..config.transforms.secret_refs import load_secrets_map
        from ..manifest.reader import load_manifest

        config = self.config
        if not isinstance(config, Config):
            return

        project_dir = str(config.project_dir or "")
        config._env_resolver = with_secrets(
            config.env_resolver,
            load_secrets_map(project_dir),
        )

        view = config.bootstrap.manifest_view
        source_raw = getattr(view, "source_raw", None) if view is not None else None
        if isinstance(source_raw, dict) and source_raw:
            scenario = getattr(config.user_env, "odpm_scenario", None)
            config.bootstrap.manifest_view = load_manifest(
                dict(source_raw),
                env_resolver=config.env_resolver,
                active_scenario=scenario,
            )

        config.generate_odoo_conf_docker_data()

    def _write_ci_secrets_runtime(self, context_dir: str) -> bool:

        if not prepare_secrets_for_ci_bake(self.config.project_dir, self.config):
            return False

        source_path = secrets_runtime_path(self.config.project_dir)
        dest_path = os.path.join(
            context_dir, constants.CI_SECRETS_RUNTIME_CONTEXT_REL_PATH
        )
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        shutil.copy2(source_path, dest_path)
        os.chmod(dest_path, 0o600)
        return True

    def _ci_context_has_baked_secrets(self) -> bool:
        path = os.path.join(
            self.config.docker_layout.ci_build_context_dir,
            constants.CI_SECRETS_RUNTIME_CONTEXT_REL_PATH,
        )
        return os.path.isfile(path)

    def _render_ci_secrets_dockerfile_block(self) -> str:
        if not self._ci_context_has_baked_secrets():
            return ""
        user = constants.CONTAINER_USER
        return (
            f"COPY --chown={user}:{user} "
            f"{constants.CI_SECRETS_RUNTIME_CONTEXT_REL_PATH} "
            f"{constants.ODPM_SECRETS_CONTAINER_PATH}\n\n"
            f"ENV {constants.ODPM_SECRETS_PATH_ENV}="
            f"{constants.ODPM_SECRETS_CONTAINER_PATH}\n\n"
        )

    def _read_ci_dockerignore_template(self) -> str:
        template_path = os.path.join(
            self.config.program_dir,
            constants.PROGRAM_CI_DOCKERIGNORE_TEMPLATE_FILE_RELATIVE_PATH,
        )
        with open(template_path) as reader:
            return reader.read()

    def prepare_ci_build_context(self) -> None:
        self._ensure_odoo_config_data_for_bake()

        context_dir = self.config.docker_layout.ci_build_context_dir
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
            self.config.docker_layout.odoo_config_data,
            os.path.join(context_dir, constants.ODOO_CONF_NAME),
        )
        dockerignore_path = os.path.join(context_dir, constants.DOCKERIGNORE)
        with open(dockerignore_path, "w") as writer:
            writer.write(self._read_ci_dockerignore_template())

        self._copy_dev_project_for_ci(context_dir)
        self._write_ci_venv_spec(context_dir)
        self._write_ci_runtime_config(context_dir)
        baked_secrets = self._write_ci_secrets_runtime(context_dir)

        _logger.info(
            "prepare_ci_build_context: %s (%s source tree(s), %s, %s, %s, %s%s)",
            context_dir,
            copied,
            constants.ODOO_CONF_NAME,
            constants.DEV_PROJECT_DIR,
            constants.CI_VENV_INSTALL_JSON,
            constants.CI_RUNTIME_CONFIG_CONTEXT_REL_PATH,
            (
                f", {constants.CI_SECRETS_RUNTIME_CONTEXT_REL_PATH}"
                if baked_secrets
                else ""
            ),
        )

    def generate_ci_dockerfile(self) -> str:
        """Deprecated: monolithic ``dockerfile_ci`` helper for legacy tests.

        Production builds use :mod:`dev_project.image_layers` (ADR-027).
        """
        template_path = os.path.join(
            self.config.program_dir, constants.CI_DOCKERFILE_TEMPLATE
        )
        with open(template_path) as template_file:
            content = template_file.read()
        content = content.format(
            BASE_IMAGE=BaseImageBuilder(self.env).resolve_base_image_ref(),
            DOCKER_PROJECT_DIR=self.config.docker_layout.docker_project_dir,
            CONTAINER_USER=constants.CONTAINER_USER,
            CURRENT_USER=constants.CONTAINER_USER,
            CI_VENV_INSTALL_JSON=constants.CI_VENV_INSTALL_JSON,
            CI_RUNTIME_CONFIG_CONTEXT_REL=constants.CI_RUNTIME_CONFIG_CONTEXT_REL_PATH,
            ODPM_CONFIG_PATH_ENV=constants.ODPM_CONFIG_PATH_ENV,
            ODPM_RUNTIME_CONFIG_CONTAINER_PATH=constants.ODPM_RUNTIME_CONFIG_CONTAINER_PATH,
            CI_SECRETS_DOCKERFILE_BLOCK=self._render_ci_secrets_dockerfile_block(),
        )
        content = content.replace(
            constants.MESSAGE_MARKER,
            _('Do not change this file, its content is generating automatically'),
        )
        dockerfile_path = os.path.join(
            self.config.docker_layout.ci_build_context_dir, constants.CI_DOCKERFILE
        )
        with open(dockerfile_path, "w") as writer:
            writer.write(content)
        return dockerfile_path

    def build_ci_image(self) -> None:
        """Build the final CI image via layered stages (ADR-027)."""
        from ..image_layers import run_layered_build

        run_layered_build(self.env, self.config.arguments)
