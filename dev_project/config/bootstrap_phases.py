"""Individual bootstrap phases for :class:`~dev_project.config.config.Config`."""

from __future__ import annotations

import os
from typing import TYPE_CHECKING

from ..debugger.user_env import resolve_debugger_backend_id
from ..manifest.database import merge_db_creation_from_manifest
from ..translations import _
from ..dev_mode import effective_dev_mode, merge_autoreload_requirements
from ..errors import ConfigError
from ..logging import get_module_logger
from .. import constants
from .transforms import beautify_module_list
from .transforms.env_substitution import with_secrets
from .transforms.secret_refs import load_secrets_map
from .state import project_settings_from_raw, user_settings_from_raw
from ..project_env.odoo_password_secrets import warn_hardened_plaintext_password_fields
from ..project_env.secrets import import_secrets_from_path, read_secrets_source
from ..secrets_providers.session import session_for_config

if TYPE_CHECKING:
    from .config import Config

_logger = get_module_logger(__name__)


def load_user_settings(config: Config) -> None:
    """Phase 1: create defaults if needed; expand only pre-manifest fields."""
    ctx = config._bootstrap_ctx
    arguments = getattr(config, "arguments", None)
    if arguments is not None and getattr(arguments, "secrets_file", None):
        import_secrets_from_path(config.project_dir, arguments.secrets_file)
        session = session_for_config(config)
        loaded = read_secrets_source(config.project_dir) or {}
        session.fetched = True
        session.provider_name = constants.SECRETS_PROVIDER_FILE
        session.key_count = len(loaded)
        config.bootstrap.secrets_file_imported_early = True
        config._env_resolver = with_secrets(
            config.env_resolver,
            load_secrets_map(config.project_dir),
        )

    ctx.deprecated.check_for_config()
    ctx.user_settings.get_user_settings_json()
    ctx.user_settings.get_user_settings_phase1()
    warn_hardened_plaintext_password_fields(
        config, config.bootstrap.raw_user_settings_disk
    )
    config._user = user_settings_from_raw(
        config.bootstrap.raw_user_settings,
        beautify_module_list=beautify_module_list,
    )
    config.bootstrap.developing_project = config._user.developing_project
    config.bootstrap.user_loaded = True


def finalize_user_settings_after_secrets(config: Config) -> None:
    """Phase 2: deep-expand settings after secrets ensure + availability gate.

    Preserves ``bootstrap.developing_project`` when it was already bound to a
    project link object in ``bind_developing_link`` (must not reset to a raw str).
    """
    ctx = config._bootstrap_ctx
    bound = config.bootstrap.developing_project
    ctx.user_settings.get_user_settings_phase2()
    config._user = user_settings_from_raw(
        config.bootstrap.raw_user_settings,
        beautify_module_list=beautify_module_list,
    )
    if bound and not isinstance(bound, str):
        config.bootstrap.developing_project = bound
        config._user.developing_project = bound
    else:
        config.bootstrap.developing_project = config._user.developing_project
    _apply_manifest_database_to_user_settings(config)


def bind_developing_link(config: Config) -> None:
    bootstrap = config.bootstrap
    if not bootstrap.developing_project:
        message = _("You do not set where developing project is situated. You can set it with --init command. Example: '--init file:///home/user/projects/your_directory_for_project' or directly form git repo --init https://github.com/aayartsev/odoo_demo_project.git'. You also can set it in user_settings.json file in key 'developing_project'")
        _logger.error(message)
        raise ConfigError(message)
    bootstrap.developing_project = config.handle_git_link(
        bootstrap.developing_project,
        system_type="standart",
        materialize=False,
    )
    bootstrap.developing_project_dir_path = bootstrap.developing_project.project_path
    config._developing_materializer.materialize_for_odpm_json(config)


def load_project_settings(config: Config) -> None:
    ctx = config._bootstrap_ctx
    ctx.odpm_json.get_project_odpm_json()
    ctx.odpm_json.get_odpm_settings()

    ctx.deprecated.check_file_for_deprecated_words(
        config.pd_manager.project_docker_compose_template_path
    )
    if (
        config.pd_manager.sync_templates
        and not os.path.exists(config.pd_manager.project_docker_compose_template_path)
    ):
        config.pd_manager.rebuild_docker_compose_template()

    ctx.deprecated.check_file_for_deprecated_words(config.bootstrap.repo_odpm_json)
    if not os.path.exists(config.bootstrap.repo_odpm_json):
        ctx.rewrite_odpm_json()

    config._project = project_settings_from_raw(
        config.bootstrap.raw_odpm_json,
        config.arguments,
        odoo_build_date=ctx.build_date.get_effective_odoo_build_date(),
    )
    finalize_user_settings_after_secrets(config)
    config.bootstrap.project_loaded = True


def _apply_manifest_database_to_user_settings(config: Config) -> None:
    from ..host.ports import BootstrapHandle  # noqa: PLC0415  # cycle

    view = BootstrapHandle(config=config).manifest_view
    if view is None:
        return
    config._user.db_creation_data = merge_db_creation_from_manifest(
        dict(config._user.db_creation_data or {}),
        view.source_raw,
    )


def bind_platform_link(config: Config) -> None:
    bootstrap = config.bootstrap
    bootstrap.odoo_platform_project = config.handle_git_link(
        config.odoo_git_link,
        system_type="platform",
        materialize=False,
    )
    bootstrap.odoo_src_dir = bootstrap.odoo_platform_project.get_project_path()


def normalize_project_requirements(
    config: Config, requirements_txt: list[str]
) -> list[str]:
    normalized = config.policy.normalize_requirements(
        requirements_txt,
        python_version=config.python_version,
        odoo_version=config.odoo_version,
        debugger_backend=resolve_debugger_backend_id(
            getattr(config, "user_env", None)
        ),
    )
    return merge_autoreload_requirements(
        normalized,
        effective_dev_mode(
            config.dev_mode,
            apply_dev_mode=config.policy.apply_dev_mode,
        ),
    )
