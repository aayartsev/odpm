import importlib
import sys
import unittest
import warnings

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


class DeprecatedShimImportTests(unittest.TestCase):
    def _import_fresh(self, module_name: str):
        sys.modules.pop(module_name, None)
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            importlib.import_module(module_name)
        return caught

    def test_host_config_import_emits_deprecation_warning(self):
        caught = self._import_fresh("dev_project.host_config")
        self.assertTrue(any(issubclass(item.category, DeprecationWarning) for item in caught))

    def test_host_project_env_import_emits_deprecation_warning(self):
        caught = self._import_fresh("dev_project.host_project_env")
        self.assertTrue(any(issubclass(item.category, DeprecationWarning) for item in caught))

    def test_host_start_string_builder_import_emits_deprecation_warning(self):
        caught = self._import_fresh("dev_project.host_start_string_builder")
        self.assertTrue(any(issubclass(item.category, DeprecationWarning) for item in caught))

    def test_handle_odoo_project_git_link_import_emits_deprecation_warning(self):
        caught = self._import_fresh("dev_project.handle_odoo_project_git_link")
        self.assertTrue(any(issubclass(item.category, DeprecationWarning) for item in caught))


if __name__ == "__main__":
    unittest.main()
