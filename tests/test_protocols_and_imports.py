import unittest

from dev_project.check_system import SystemChecker
from dev_project.project_env import CreateProjectEnvironment
from dev_project.protocols import (
    PrepareProjectServicesProtocol,
    RuntimeProjectServicesProtocol,
    SystemCheckerProtocol,
)


class ProtocolTypingTests(unittest.TestCase):
    def test_system_checker_satisfies_protocol(self):
        self.assertTrue(issubclass(SystemChecker, SystemCheckerProtocol))

    def test_create_project_environment_satisfies_runtime_protocol(self):
        self.assertTrue(
            issubclass(CreateProjectEnvironment, RuntimeProjectServicesProtocol)
        )

    def test_create_project_environment_is_not_prepare_services_protocol(self):
        self.assertFalse(
            issubclass(CreateProjectEnvironment, PrepareProjectServicesProtocol)
        )

    def test_prepare_service_modules_expose_prepare_operations(self):
        from dev_project.compose.generator import ComposeGenerator
        from dev_project.project_env.links import ProjectLinks
        from dev_project.project_env.templates import ProjectTemplates

        for name in ("map_folders", "checkout_dependencies", "update_links"):
            self.assertTrue(callable(getattr(ProjectLinks, name)))
        for name in (
            "generate_dockerfile",
            "generate_dockerignore",
            "generate_config_file",
        ):
            self.assertTrue(callable(getattr(ProjectTemplates, name)))
        self.assertTrue(callable(ComposeGenerator.generate_docker_compose_file))

    def test_runtime_checkable_protocols(self):
        self.assertTrue(isinstance(SystemCheckerProtocol, type))
        self.assertTrue(getattr(SystemCheckerProtocol, "_is_runtime_protocol", False))
        self.assertTrue(
            getattr(RuntimeProjectServicesProtocol, "_is_runtime_protocol", False)
        )
        self.assertTrue(
            getattr(PrepareProjectServicesProtocol, "_is_runtime_protocol", False)
        )


class CanonicalImportSmokeTests(unittest.TestCase):
    def test_config_package_imports(self):
        from dev_project import config as config_module

        self.assertTrue(hasattr(config_module, "Config"))

    def test_config_has_no_system_checker_backref(self):
        from dev_project.config import Config

        self.assertFalse(hasattr(Config, "system_checker"))

    def test_config_runtime_fields_are_properties(self):
        from dev_project.config import Config

        for name in (
            "compose_service",
            "container_run_mode",
            "no_log_prefix",
            "docker_compose_command",
        ):
            self.assertIsInstance(getattr(Config, name), property)

    def test_project_env_package_imports(self):
        from dev_project import project_env as project_env_module

        self.assertTrue(hasattr(project_env_module, "CreateProjectEnvironment"))

    def test_git_package_imports(self):
        from dev_project import git as git_module

        self.assertTrue(hasattr(git_module, "HandleOdooProjectLink"))

    def test_compose_package_imports(self):
        from dev_project import compose as compose_module
        from dev_project.compose import (
            ComposeGenerator,
            ComposeOdooService,
            ComposeServiceBuilder,
            StartCommand,
            should_force_recreate_compose,
        )
        from dev_project.compose.command_render import yaml_scalar
        from dev_project.compose.runtime import should_force_recreate_compose as runtime_fn

        self.assertTrue(hasattr(compose_module, "ComposeServiceBuilder"))
        self.assertTrue(hasattr(compose_module, "ComposeGenerator"))
        self.assertTrue(hasattr(compose_module, "StartCommand"))
        self.assertTrue(callable(should_force_recreate_compose))
        self.assertIs(should_force_recreate_compose, runtime_fn)
        self.assertTrue(callable(yaml_scalar))
        self.assertTrue(hasattr(ComposeOdooService, "__dataclass_fields__"))
        self.assertTrue(hasattr(ComposeServiceBuilder, "build"))
        self.assertTrue(hasattr(ComposeGenerator, "render_docker_compose_content"))
        self.assertTrue(hasattr(StartCommand, "__dataclass_fields__"))

    def test_project_materializer_imports(self):
        from dev_project import project_materializer as materializer_module

        self.assertTrue(hasattr(materializer_module, "ProjectMaterializer"))

    def test_host_package_imports(self):
        from dev_project import host as host_module
        from dev_project.host.cli import OdpmCliArgs, parse_cli_args

        self.assertTrue(hasattr(host_module, "CreateUserEnvironment"))
        self.assertTrue(hasattr(host_module, "HostProjectContext"))
        self.assertTrue(hasattr(host_module, "HostRuntimeState"))
        self.assertTrue(callable(parse_cli_args))
        self.assertTrue(hasattr(OdpmCliArgs, "__dataclass_fields__"))

    def test_config_bootstrap_imports(self):
        from dev_project.config import bootstrap as bootstrap_module

        self.assertTrue(callable(bootstrap_module.bootstrap_config))

    def test_config_layout_imports(self):
        from dev_project.config import layout as layout_module

        self.assertTrue(callable(layout_module.apply_policy_and_layout))

    def test_config_runtime_facade_imports(self):
        from dev_project.config.runtime_facade import ConfigRuntimeFacadeMixin

        self.assertTrue(hasattr(ConfigRuntimeFacadeMixin, "compose_service"))

    def test_cli_entrypoint_imports(self):
        from dev_project.cli import main

        self.assertTrue(callable(main))

    def test_plan_module_imports(self):
        from dev_project.plan import OdpmPlanner, PlanStep, format_plan
        from dev_project.plan.cli import is_plan_mode
        from dev_project.plan.format import format_plan_json, format_plan_table

        self.assertTrue(callable(OdpmPlanner.build))
        self.assertTrue(callable(is_plan_mode))
        self.assertTrue(callable(format_plan))
        self.assertTrue(callable(format_plan_table))
        self.assertTrue(callable(format_plan_json))
        self.assertTrue(hasattr(PlanStep, "__dataclass_fields__"))

    def test_plan_package_imports(self):
        from dev_project import plan as plan_module
        from dev_project.plan import (
            OdpmPlanner,
            PlanStep,
            deps_lock_file_exists,
            project_template_needs_upgrade,
        )
        from dev_project.plan.compose_preview import preview_compose_service
        from dev_project.plan.compose_runtime import compose_up_would_run
        from dev_project.plan.core import OdpmPlan, runtime_config_stale
        from dev_project.plan.diff import PlanFileDiff, build_plan_diffs
        from dev_project.plan.runtime_preview import preview_runtime_config_text

        self.assertTrue(hasattr(plan_module, "OdpmPlanner"))
        self.assertTrue(hasattr(plan_module, "PlanStep"))
        self.assertTrue(callable(deps_lock_file_exists))
        self.assertTrue(callable(project_template_needs_upgrade))
        self.assertTrue(callable(preview_compose_service))
        self.assertTrue(callable(compose_up_would_run))
        self.assertTrue(callable(runtime_config_stale))
        self.assertTrue(hasattr(OdpmPlan, "__dataclass_fields__"))
        self.assertTrue(hasattr(PlanFileDiff, "__dataclass_fields__"))
        self.assertTrue(callable(build_plan_diffs))
        self.assertTrue(callable(preview_runtime_config_text))

    def test_prepare_package_imports(self):
        from dev_project import prepare as prepare_module
        from dev_project.prepare import (
            PREPARE_STEPS,
            PrepareContext,
            build_prepare_plan,
            evaluate_prepare_plan,
            make_prepare_context,
        )

        self.assertTrue(hasattr(prepare_module, "make_prepare_context"))
        self.assertTrue(hasattr(PREPARE_STEPS, "__len__"))
        self.assertTrue(hasattr(PrepareContext, "__dataclass_fields__"))
        self.assertTrue(callable(build_prepare_plan))
        self.assertTrue(callable(evaluate_prepare_plan))
        self.assertTrue(callable(make_prepare_context))

    def test_program_dir_resolver_imports(self):
        from dev_project.program_dir import resolve_program_dir

        self.assertTrue(callable(resolve_program_dir))

    def test_run_odoo_entrypoint_imports(self):
        from dev_project.inside_docker_app import run_odoo as run_odoo_module

        self.assertTrue(callable(run_odoo_module.main))

    def test_inside_docker_app_logger_reexports_canonical_logging(self):
        from dev_project import logging as canonical_logging
        from dev_project.inside_docker_app import logger as legacy_logger

        self.assertIs(legacy_logger.get_module_logger, canonical_logging.get_module_logger)
        self.assertIs(legacy_logger.CustomFormatter, canonical_logging.CustomFormatter)


if __name__ == "__main__":
    unittest.main()
