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

    def test_project_env_package_imports(self):
        from dev_project import project_env as project_env_module

        self.assertTrue(hasattr(project_env_module, "CreateProjectEnvironment"))

    def test_git_package_imports(self):
        from dev_project import git as git_module

        self.assertTrue(hasattr(git_module, "HandleOdooProjectLink"))

    def test_compose_service_builder_imports(self):
        from dev_project import compose_service_builder as builder_module

        self.assertTrue(hasattr(builder_module, "ComposeServiceBuilder"))

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
