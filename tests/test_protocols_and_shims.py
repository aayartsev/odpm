import unittest

from dev_project.check_system import SystemChecker
from dev_project.project_env import CreateProjectEnvironment
from dev_project.protocols import (
    CreateProjectEnvironmentProtocol,
    SystemCheckerProtocol,
)


class ProtocolTypingTests(unittest.TestCase):
    def test_system_checker_satisfies_protocol(self):
        self.assertTrue(issubclass(SystemChecker, SystemCheckerProtocol))

    def test_create_project_environment_satisfies_protocol(self):
        self.assertTrue(
            issubclass(CreateProjectEnvironment, CreateProjectEnvironmentProtocol)
        )

    def test_runtime_checkable_protocols(self):
        self.assertTrue(isinstance(SystemCheckerProtocol, type))
        self.assertTrue(getattr(SystemCheckerProtocol, "_is_runtime_protocol", False))
        self.assertTrue(
            getattr(CreateProjectEnvironmentProtocol, "_is_runtime_protocol", False)
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

    def test_compose_service_builder_imports(self):
        from dev_project import compose_service_builder as builder_module
        from dev_project.compose import ComposeServiceBuilder as canonical_builder

        self.assertTrue(hasattr(builder_module, "ComposeServiceBuilder"))
        self.assertIs(builder_module.ComposeServiceBuilder, canonical_builder)

    def test_compose_package_imports(self):
        from dev_project import compose as compose_module
        from dev_project.compose import (
            ComposeGenerator,
            ComposeOdooService,
            ComposeServiceBuilder,
            StartCommand,
            should_force_recreate_compose,
        )

        self.assertTrue(hasattr(compose_module, "ComposeServiceBuilder"))
        self.assertTrue(hasattr(compose_module, "ComposeGenerator"))
        self.assertTrue(hasattr(compose_module, "StartCommand"))
        self.assertTrue(callable(should_force_recreate_compose))
        self.assertTrue(hasattr(ComposeOdooService, "__dataclass_fields__"))
        self.assertTrue(hasattr(ComposeServiceBuilder, "build"))
        self.assertTrue(hasattr(ComposeGenerator, "render_docker_compose_content"))
        self.assertTrue(hasattr(StartCommand, "__dataclass_fields__"))

    def test_compose_shim_imports(self):
        from dev_project import compose_runtime as compose_runtime_module
        from dev_project import compose_command_render as command_render_module
        from dev_project import start_command as start_command_module
        from dev_project.compose.runtime import should_force_recreate_compose
        from dev_project.compose.command_render import yaml_scalar
        from dev_project.compose.start_command import StartCommand

        self.assertTrue(hasattr(compose_runtime_module, "should_force_recreate_compose"))
        self.assertIs(
            compose_runtime_module.should_force_recreate_compose,
            should_force_recreate_compose,
        )
        self.assertTrue(hasattr(command_render_module, "yaml_scalar"))
        self.assertIs(command_render_module.yaml_scalar, yaml_scalar)
        self.assertTrue(hasattr(start_command_module, "StartCommand"))
        self.assertIs(start_command_module.StartCommand, StartCommand)

    def test_compose_generator_shim_imports(self):
        from dev_project.project_env import compose as compose_shim_module
        from dev_project.compose import ComposeGenerator as canonical_generator

        self.assertTrue(hasattr(compose_shim_module, "ComposeGenerator"))
        self.assertIs(compose_shim_module.ComposeGenerator, canonical_generator)

    def test_project_materializer_imports(self):
        from dev_project import project_materializer as materializer_module

        self.assertTrue(hasattr(materializer_module, "ProjectMaterializer"))

    def test_host_context_imports(self):
        from dev_project import host_context as host_context_module
        from dev_project import host as host_module

        self.assertTrue(hasattr(host_context_module, "HostProjectContext"))
        self.assertTrue(hasattr(host_module, "HostProjectContext"))

    def test_host_runtime_imports(self):
        from dev_project import host_runtime as host_runtime_module
        from dev_project import host as host_module

        self.assertTrue(hasattr(host_runtime_module, "HostRuntimeState"))
        self.assertTrue(hasattr(host_module, "HostRuntimeState"))

    def test_host_package_imports(self):
        from dev_project import host as host_module
        from dev_project.host.cli import OdpmCliArgs, parse_cli_args

        self.assertTrue(hasattr(host_module, "CreateUserEnvironment"))
        self.assertTrue(hasattr(host_module, "HostProjectContext"))
        self.assertTrue(callable(parse_cli_args))
        self.assertTrue(hasattr(OdpmCliArgs, "__dataclass_fields__"))

    def test_host_cli_shim_imports(self):
        from dev_project import host_cli as host_cli_module
        from dev_project.host_cli.args import OdpmCliArgs
        from dev_project.host_cli.parse_args import parse_cli_args

        self.assertTrue(hasattr(host_cli_module, "OdpmCliArgs"))
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
        from dev_project.plan.cli import is_plan_mode as canonical_is_plan_mode
        from dev_project.plan.format import format_plan_json, format_plan_table
        from dev_project.plan_cli import is_plan_mode
        from dev_project.plan_format import format_plan_json as shim_format_plan_json

        self.assertTrue(callable(OdpmPlanner.build))
        self.assertTrue(callable(is_plan_mode))
        self.assertIs(is_plan_mode, canonical_is_plan_mode)
        self.assertTrue(callable(format_plan))
        self.assertTrue(callable(format_plan_table))
        self.assertTrue(callable(format_plan_json))
        self.assertIs(format_plan_json, shim_format_plan_json)
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

    def test_plan_shim_imports(self):
        from dev_project import plan_compose_preview as compose_preview_shim
        from dev_project import plan_compose_runtime as compose_runtime_shim
        from dev_project import plan_diff as diff_shim
        from dev_project import plan_runtime_preview as runtime_preview_shim
        from dev_project.plan.compose_preview import compose_service_needs_update
        from dev_project.plan.compose_runtime import evaluate_compose_up_plan
        from dev_project.plan.diff import PlanFileDiff
        from dev_project.plan.runtime_preview import clear_runtime_config_preview_cache

        self.assertIs(
            compose_preview_shim.compose_service_needs_update,
            compose_service_needs_update,
        )
        self.assertIs(
            compose_runtime_shim.evaluate_compose_up_plan,
            evaluate_compose_up_plan,
        )
        self.assertIs(diff_shim.PlanFileDiff, PlanFileDiff)
        self.assertIs(
            runtime_preview_shim.clear_runtime_config_preview_cache,
            clear_runtime_config_preview_cache,
        )

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
