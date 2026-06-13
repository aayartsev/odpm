import unittest
from unittest.mock import MagicMock

from dev_project.inside_docker_app.odoo_checker.dispatch import (
    checker_cli_flags,
    run_checker_operations,
)

from tests.container_config_helpers import minimal_container_config


class CheckerCliFlagsTests(unittest.TestCase):
    def test_reads_db_name_from_arguments(self):
        flags = checker_cli_flags({"d": "demo"})
        self.assertEqual(flags.db_name, "demo")


class RunCheckerOperationsTests(unittest.TestCase):
    def test_run_checker_operations_invokes_db_and_admin_ops(self):
        config = minimal_container_config(
            arguments={"d": "demo", "set_admin_pass": True},
            sql_queries=[],
            modules_to_update=[],
        )
        flags = checker_cli_flags(config.arguments)
        runtime = MagicMock()
        runtime.environment_manage.return_value.__enter__ = lambda self: None
        runtime.environment_manage.return_value.__exit__ = lambda *args: None
        db_ops = MagicMock()
        admin_ops = MagicMock()
        sql_runner = MagicMock()
        i18n_ops = MagicMock()

        run_checker_operations(
            config,
            flags,
            runtime,
            db_ops=db_ops,
            admin_ops=admin_ops,
            sql_runner=sql_runner,
            i18n_ops=i18n_ops,
        )

        db_ops.ensure_database_exists.assert_called_once_with("demo")
        admin_ops.set_admin_password.assert_called_once()
        sql_runner.execute_queries.assert_not_called()
        i18n_ops.export_po_files.assert_not_called()

    def test_run_checker_operations_noops_without_db_or_list_flag(self):
        config = minimal_container_config(arguments={})
        flags = checker_cli_flags(config.arguments)
        runtime = MagicMock()
        db_ops = MagicMock()

        run_checker_operations(
            config,
            flags,
            runtime,
            db_ops=db_ops,
            admin_ops=MagicMock(),
            sql_runner=MagicMock(),
            i18n_ops=MagicMock(),
        )

        runtime.environment_manage.assert_not_called()
        db_ops.ensure_database_exists.assert_not_called()


if __name__ == "__main__":
    unittest.main()
