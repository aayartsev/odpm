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

        self.assertTrue(hasattr(builder_module, "ComposeServiceBuilder"))

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
        from dev_project.plan_cli import is_plan_mode
        from dev_project.plan_format import format_plan_json, format_plan_table

        self.assertTrue(callable(OdpmPlanner.build))
        self.assertTrue(callable(is_plan_mode))
        self.assertTrue(callable(format_plan))
        self.assertTrue(callable(format_plan_table))
        self.assertTrue(callable(format_plan_json))
        self.assertTrue(hasattr(PlanStep, "__dataclass_fields__"))

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
