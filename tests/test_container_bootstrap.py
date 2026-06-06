import base64
import json
import unittest
from unittest.mock import patch

from dev_project import constants
from dev_project.inside_docker_app.container_bootstrap import main, prepare_venv
from dev_project.inside_docker_app.exceptions import VenvError
from dev_project.inside_docker_app.utils import resolve_venv_is_baked, resolve_venv_mode

from tests.container_config_helpers import (
    minimal_container_config,
    minimal_container_config_dict,
)


def _b64_config(**overrides) -> str:
    payload = minimal_container_config_dict(**overrides)
    return base64.b64encode(json.dumps(payload).encode()).decode()


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


class ContainerBootstrapMainTests(unittest.TestCase):
    @patch("dev_project.inside_docker_app.container_bootstrap.run_container_bootstrap")
    @patch("dev_project.inside_docker_app.container_bootstrap.parse_args")
    def test_main_exits_with_container_error_code(self, mock_parse_args, mock_bootstrap):
        from dev_project.inside_docker_app import container_bootstrap

        mock_parse_args.return_value.config_base64_data = _b64_config()
        mock_bootstrap.side_effect = VenvError("baked venv missing", exit_code=1)

        with patch.object(container_bootstrap.sys, "exit") as mock_exit:
            with self.assertWarns(DeprecationWarning):
                main()
            mock_exit.assert_called_once_with(1)

    @patch("dev_project.inside_docker_app.container_bootstrap.run_container_bootstrap")
    @patch("dev_project.inside_docker_app.container_bootstrap.parse_args")
    def test_main_propagates_custom_exit_code(self, mock_parse_args, mock_bootstrap):
        from dev_project.inside_docker_app import container_bootstrap
        from dev_project.inside_docker_app.exceptions import PostgresError

        mock_parse_args.return_value.config_base64_data = _b64_config()
        mock_bootstrap.side_effect = PostgresError("psycopg2 missing", exit_code=2)

        with patch.object(container_bootstrap.sys, "exit") as mock_exit:
            with self.assertWarns(DeprecationWarning):
                main()
            mock_exit.assert_called_once_with(2)


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
