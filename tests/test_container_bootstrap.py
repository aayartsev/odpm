import unittest
from unittest.mock import patch

from dev_project import constants
from dev_project.inside_docker_app.container_bootstrap import (
    prepare_venv,
    run_container_bootstrap,
)
from dev_project.inside_docker_app.exceptions import VenvError
from dev_project.inside_docker_app.utils import resolve_venv_is_baked, resolve_venv_mode

from tests.container_config_helpers import minimal_container_config


class ResolveVenvIsBakedTests(unittest.TestCase):
    def test_venv_mode_baked(self):
        self.assertTrue(
            resolve_venv_is_baked(
                minimal_container_config(venv_mode=constants.VENV_MODE_BAKED)
            )
        )

    def test_venv_mode_fresh(self):
        self.assertFalse(
            resolve_venv_is_baked(
                minimal_container_config(venv_mode=constants.VENV_MODE_FRESH)
            )
        )

    def test_legacy_ci_scenario_fallback(self):
        self.assertTrue(
            resolve_venv_is_baked(
                minimal_container_config(
                    odpm_scenario=constants.CI_SCENARIO,
                    venv_mode=None,
                )
            )
        )

    def test_legacy_developer_scenario_fallback(self):
        self.assertFalse(
            resolve_venv_is_baked(
                minimal_container_config(
                    odpm_scenario=constants.DEVELOPER_SCENARIO,
                    venv_mode=None,
                )
            )
        )

    def test_venv_mode_takes_priority_over_legacy_scenario(self):
        self.assertFalse(
            resolve_venv_is_baked(
                minimal_container_config(
                    venv_mode=constants.VENV_MODE_FRESH,
                    odpm_scenario=constants.CI_SCENARIO,
                )
            )
        )


class ResolveVenvModeTests(unittest.TestCase):
    def test_resolve_venv_mode_matches_policy(self):
        self.assertEqual(
            resolve_venv_mode(
                minimal_container_config(venv_mode=constants.VENV_MODE_BAKED)
            ),
            constants.VENV_MODE_BAKED,
        )


class PrepareVenvTests(unittest.TestCase):
    @patch("dev_project.inside_docker_app.container_bootstrap.VirtualenvChecker")
    def test_prepare_venv_uses_config_venv_mode(self, checker_cls):
        config = minimal_container_config(venv_mode=constants.VENV_MODE_BAKED)
        prepare_venv(config)
        checker_cls.assert_called_once_with(config)


class RunContainerBootstrapTests(unittest.TestCase):
    @patch("dev_project.inside_docker_app.container_bootstrap.OdooChecker")
    @patch("dev_project.inside_docker_app.container_bootstrap.prepare_venv")
    def test_run_container_bootstrap_runs_prepare_and_odoo_checker(
        self, mock_prepare, mock_odoo_checker
    ):
        config = minimal_container_config()
        run_container_bootstrap(config)
        mock_prepare.assert_called_once_with(config)
        mock_odoo_checker.assert_called_once_with(config)

    @patch("dev_project.inside_docker_app.container_bootstrap.OdooChecker")
    @patch("dev_project.inside_docker_app.container_bootstrap.prepare_venv")
    def test_run_container_bootstrap_propagates_venv_error(
        self, mock_prepare, _mock_odoo_checker
    ):
        config = minimal_container_config()
        mock_prepare.side_effect = VenvError("baked venv missing", exit_code=1)
        with self.assertRaises(VenvError) as ctx:
            run_container_bootstrap(config)
        self.assertEqual(ctx.exception.exit_code, 1)


class PostgresWaiterErrorTests(unittest.TestCase):
    def test_wait_for_postgres_timeout_raises_postgres_error(self):
        from dev_project.inside_docker_app.exceptions import PostgresError
        from dev_project.inside_docker_app.odoo_checker.postgres_waiter import PostgresWaiter

        waiter = PostgresWaiter(timeout=0, check_interval=0)
        with patch.object(waiter, "is_postgres_up", return_value=False):
            with self.assertRaises(PostgresError) as ctx:
                waiter.wait_for_postgres()
        self.assertEqual(ctx.exception.exit_code, 1)

    def test_wait_for_postgres_db_missing_psycopg2_raises(self):
        import builtins

        from dev_project.inside_docker_app.exceptions import PostgresError
        from dev_project.inside_docker_app.odoo_checker.postgres_waiter import PostgresWaiter

        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "psycopg2":
                raise ImportError("no psycopg2")
            return real_import(name, *args, **kwargs)

        waiter = PostgresWaiter()
        with patch.object(builtins, "__import__", side_effect=fake_import):
            with self.assertRaises(PostgresError) as ctx:
                waiter.wait_for_postgres_db("postgres", "odoo", "odoo")
        self.assertEqual(ctx.exception.exit_code, 2)


if __name__ == "__main__":
    unittest.main()
