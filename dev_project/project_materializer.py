"""Orchestrate host-side project file generation (git, templates, compose)."""

from __future__ import annotations

from argparse import Namespace

from .compose_service_builder import ComposeServiceBuilder
from .config import Config
from .errors import PipelineError
from .git.deps_lock_manager import DepsLockManager
from .logging import get_module_logger
from .project_env import CreateProjectEnvironment
from .protocols import SystemCheckerProtocol

_logger = get_module_logger(__name__)


class ProjectMaterializer:
    """Run the prepare-phase side effects for a host project."""

    def run(
        self,
        config: Config,
        project_env: CreateProjectEnvironment,
        system_checker: SystemCheckerProtocol,
        args: Namespace,
    ) -> None:
        skip_git = getattr(args, "no_git_update", False)
        update_lock = getattr(args, "update_lock", False)
        if update_lock and skip_git:
            message = "--update-lock cannot be used together with --no-git-update"
            _logger.error(message)
            raise PipelineError(message, exit_code=1)

        lock_manager = DepsLockManager(config)
        if not skip_git and not update_lock:
            lock_manager.load()
            lock_manager.enter_apply_mode()

        if skip_git:
            config.ensure_git_repos_present()
        else:
            config.materialize_git_repos(
                skip_build_date=lock_manager.has_platform_lock()
            )
        project_env.map_folders()
        lock_manager.apply_to_platform(config.odoo_platform_project)
        lock_manager.apply_to_developing(config.developing_project)
        lock_manager.apply_to_dependencies(config.dependencies_projects)
        project_env.generate_dockerfile()
        project_env.generate_dockerignore()
        system_checker.check_docker()
        system_checker.check_running_containers()
        project_env.generate_config_file()
        ComposeServiceBuilder(config).build()
        project_env.generate_docker_compose_file()
        system_checker.check_docker_compose()
        if not skip_git:
            project_env.checkout_dependencies(lock_manager=lock_manager)
            if update_lock:
                lock_manager.collect_and_save(
                    developing=config.developing_project,
                )
            elif lock_manager.apply_mode:
                lock_manager.verify_after_checkout(
                    platform=config.odoo_platform_project,
                    developing=config.developing_project,
                    dependencies=config.dependencies_projects,
                )
        project_env.update_links()
