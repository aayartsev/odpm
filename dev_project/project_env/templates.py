from __future__ import annotations

import os
from typing import TYPE_CHECKING, Any

from .. import constants
from ..translations import _
from ..config.odoo_conf import odoo_conf_on_disk_needs_regeneration

if TYPE_CHECKING:
    from .environment import CreateProjectEnvironment


def render_dockerfile_content(host_ctx: Any) -> str:
    """Render root Dockerfile text from the project's ``.odpm`` template."""
    policy = host_ctx.policy
    with open(host_ctx.docker_layout.project_dockerfile_template_path) as reader:
        content = reader.read()
    content = content.format(
        PROCESSOR_ARCH=host_ctx.project_settings.arch,
        CONTAINER_USER_UID=policy.runtime_unix_uid(),
        CONTAINER_USER_GID=policy.runtime_unix_gid(),
        CONTAINER_USER=policy.runtime_unix_user(),
        CONTAINER_PASSWORD=policy.runtime_unix_password(),
        CURRENT_USER_UID=policy.runtime_unix_uid(),
        CURRENT_USER_GID=policy.runtime_unix_gid(),
        CURRENT_USER=policy.runtime_unix_user(),
        CURRENT_PASSWORD=policy.runtime_unix_password(),
        PYTHON_VERSION=host_ctx.project_settings.python_version,
        DISTRO_NAME=host_ctx.project_settings.distro_name,
        DISTRO_VERSION=host_ctx.project_settings.distro_version,
        DISTRO_VERSION_CODENAME=host_ctx.project_settings.distro_version_codename,
    )
    return content.replace(
        _("If you want drop this file to default values, just delete it"),
        _("Do not change this file, its content is generating automatically"),
    )


def dockerfile_on_disk_needs_regeneration(host_ctx: Any) -> bool:
    """True when root Dockerfile is missing or differs from the ``.odpm`` template.

    ``ensure_project_template`` may refresh ``.odpm/debian_*_dockerfile*`` by
    content hash while ``template.dockerfile`` would otherwise stay noop (markers
    still present and ``base_image_identity`` still matches the stale root file).
    """
    dockerfile_path = os.path.join(host_ctx.project_dir, constants.DOCKERFILE)
    if not os.path.isfile(dockerfile_path):
        return True
    expected = render_dockerfile_content(host_ctx)
    with open(dockerfile_path, encoding="utf-8") as reader:
        return reader.read() != expected


class ProjectTemplates:
    def __init__(self, env: CreateProjectEnvironment) -> None:
        self.env = env

    def generate_dockerfile(self) -> None:
        host_ctx = self.env.host_ctx
        content = render_dockerfile_content(host_ctx)
        dockerfile_path = os.path.join(host_ctx.project_dir, constants.DOCKERFILE)
        self.env.bootstrap.dockerfile_path = dockerfile_path
        with open(dockerfile_path, "w") as writer:
            writer.write(content)

    def generate_dockerignore(self) -> None:
        host_ctx = self.env.host_ctx
        with open(host_ctx.docker_layout.project_dockerignore_template_path) as reader:
            content = reader.read()
        content = content.replace(
            _('If you want drop this file to default values, just delete it'),
            _('Do not change this file, its content is generating automatically'),
        )
        dockerignore_path = os.path.join(host_ctx.project_dir, constants.DOCKERIGNORE)
        with open(dockerignore_path, "w") as writer:
            writer.write(content)

    def generate_config_file(self) -> None:
        host_ctx = self.env.host_ctx
        config_file_template_path = os.path.join(
            host_ctx.project_dir,
            constants.PROJECT_ODOO_TEMPLATE_CONFIG_FILE_RELATIVE_PATH,
        )
        with open(config_file_template_path) as reader:
            content = reader.read()
        postgres_host = host_ctx.user_env.postgres_service_name
        for replace_phrase in {
            constants.DO_NOT_CHANGE_PARAM: _('Do not change this param, it is generating automatically'),
            constants.ADMIN_PASSWD_MESSAGE: _('Do not change, it will get from "db_manager_password" param from config.json file'),
            constants.MESSAGE_MARKER: _('If you want drop this file to default values, just delete it'),
            constants.POSTGRES_ODOO_USER_MARKER: constants.POSTGRES_ODOO_USER,
            constants.POSTGRES_ODOO_PASS_MARKER: constants.POSTGRES_ODOO_PASS,
            constants.POSTGRES_ODOO_HOST_MARKER: postgres_host,
            constants.POSTGRES_ODOO_PORT_MARKER: str(constants.POSTGRES_ODOO_PORT),
            constants.ODOO_PORT_MARKER: str(constants.ODOO_DOCKER_PORT),
        }.items():
            content = content.replace(replace_phrase[0], replace_phrase[1])
        if odoo_conf_on_disk_needs_regeneration(
            host_ctx.docker_layout.path_odoo_conf,
            expected_db_host=postgres_host,
        ) or self.env.bootstrap.pd_manager.check_project_odoo_config_template(
            config_file_template_path
        ):
            with open(host_ctx.docker_layout.path_odoo_conf, "w") as writer:
                writer.write(content)
