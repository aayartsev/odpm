"""Tests for SystemCheckPolicy gating matrix (including ADR-017 CI prepare-only)."""

import unittest
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.prepare.steps_compose import evaluate_compose_validate
from dev_project.prepare.steps_docker import (
    evaluate_docker_engine_check,
    evaluate_docker_ports_release,
)
from dev_project.scenario_policy import ScenarioPolicy
from dev_project.system_check_policy import (
    SystemCheckPolicy,
    cli_allows_ci_explicit_mode,
    is_ci_prepare_only,
    merged_environ_for_resolve,
)


class SystemCheckPolicyMatrixTests(unittest.TestCase):
    def _config(
        self,
        *,
        check_system: bool,
        scenario: str,
        arguments: OdpmCliArgs | None = None,
        dotenv: dict[str, str] | None = None,
    ) -> MagicMock:
        config = MagicMock()
        config.user_settings = MagicMock()
        config.user_settings.check_system = check_system
        config.policy = ScenarioPolicy.from_scenario(scenario)
        config.arguments = arguments if arguments is not None else OdpmCliArgs()
        user_env = MagicMock()
        user_env.project_dotenv_dict.return_value = dict(dotenv or {})
        config.user_env = user_env
        return config

    def _host_ctx(
        self,
        *,
        check_system: bool,
        scenario: str,
        arguments: OdpmCliArgs | None = None,
        dotenv: dict[str, str] | None = None,
    ) -> MagicMock:
        config = self._config(
            check_system=check_system,
            scenario=scenario,
            arguments=arguments,
            dotenv=dotenv,
        )
        host_ctx = MagicMock()
        host_ctx.user_settings = config.user_settings
        host_ctx.policy = config.policy
        host_ctx.arguments = config.arguments
        host_ctx.user_env = config.user_env
        return host_ctx

    def test_from_config_developer_check_system_enabled(self):
        policy = SystemCheckPolicy.from_config(
            self._config(check_system=True, scenario=constants.DEVELOPER_SCENARIO)
        )
        self.assertTrue(policy.beginner_git)
        self.assertTrue(policy.beginner_docker)
        self.assertTrue(policy.developer_port_release)
        self.assertTrue(policy.compose_validate)
        self.assertTrue(policy.file_system_on_init)
        self.assertFalse(policy.skip_docker_daemon)
        self.assertFalse(policy.require_ci_explicit_mode)

    def test_from_config_developer_check_system_disabled(self):
        policy = SystemCheckPolicy.from_config(
            self._config(check_system=False, scenario=constants.DEVELOPER_SCENARIO)
        )
        self.assertFalse(policy.beginner_git)
        self.assertFalse(policy.beginner_docker)
        self.assertTrue(policy.developer_port_release)
        self.assertTrue(policy.compose_validate)
        self.assertTrue(policy.file_system_on_init)

    def test_from_config_server_scenario(self):
        policy = SystemCheckPolicy.from_config(
            self._config(check_system=True, scenario=constants.SERVER_SCENARIO)
        )
        self.assertTrue(policy.beginner_git)
        self.assertTrue(policy.beginner_docker)
        self.assertFalse(policy.developer_port_release)

    def test_ci_kaniko_direct_skip_start_skips_daemon_keeps_validate(self):
        args = OdpmCliArgs(skip_start=True)
        dotenv = {
            constants.ODPM_CI_IMAGE_BUILDER_ENV: "kaniko",
            constants.ODPM_KANIKO_EXECUTOR_MODE_ENV: "direct",
        }
        policy = SystemCheckPolicy.from_config(
            self._config(
                check_system=True,
                scenario=constants.CI_SCENARIO,
                arguments=args,
                dotenv=dotenv,
            )
        )
        self.assertTrue(policy.require_ci_explicit_mode)
        self.assertTrue(policy.skip_docker_daemon)
        self.assertTrue(policy.skip_compose_cli_probe)
        self.assertTrue(policy.skip_ensure_base_local)
        self.assertTrue(policy.relaxed_file_system)
        self.assertTrue(policy.compose_validate)

    def test_ci_kaniko_docker_run_does_not_skip_daemon(self):
        args = OdpmCliArgs(build_image=True)
        dotenv = {
            constants.ODPM_CI_IMAGE_BUILDER_ENV: "kaniko",
            constants.ODPM_KANIKO_EXECUTOR_MODE_ENV: "docker-run",
        }
        policy = SystemCheckPolicy.from_config(
            self._config(
                check_system=True,
                scenario=constants.CI_SCENARIO,
                arguments=args,
                dotenv=dotenv,
            )
        )
        self.assertFalse(policy.skip_docker_daemon)
        self.assertTrue(policy.skip_ensure_base_local)

    def test_ci_docker_builder_skips_ensure_base_false(self):
        args = OdpmCliArgs(skip_start=True)
        policy = SystemCheckPolicy.from_config(
            self._config(
                check_system=True,
                scenario=constants.CI_SCENARIO,
                arguments=args,
                dotenv={constants.ODPM_CI_IMAGE_BUILDER_ENV: "docker"},
            )
        )
        self.assertFalse(policy.skip_ensure_base_local)
        self.assertFalse(policy.skip_docker_daemon)

    def test_prepare_step_matrix(self):
        cases = (
            (
                constants.DEVELOPER_SCENARIO,
                True,
                ("run", "run", "run"),
            ),
            (
                constants.DEVELOPER_SCENARIO,
                False,
                ("skip", "run", "run"),
            ),
            (
                constants.SERVER_SCENARIO,
                True,
                ("run", "skip", "run"),
            ),
            (
                constants.CI_SCENARIO,
                False,
                ("skip", "skip", "run"),
            ),
        )
        for scenario, check_system, expected in cases:
            with self.subTest(scenario=scenario, check_system=check_system):
                ctx = MagicMock()
                ctx.host_ctx = self._host_ctx(
                    check_system=check_system, scenario=scenario
                )
                docker = evaluate_docker_engine_check(ctx)
                ports = evaluate_docker_ports_release(ctx)
                compose = evaluate_compose_validate(ctx)
                self.assertEqual(
                    (docker.outcome, ports.outcome, compose.outcome),
                    expected,
                )

    def test_prepare_step_kaniko_direct_skips_docker_keeps_compose_validate(self):
        ctx = MagicMock()
        ctx.host_ctx = self._host_ctx(
            check_system=True,
            scenario=constants.CI_SCENARIO,
            arguments=OdpmCliArgs(skip_start=True),
            dotenv={
                constants.ODPM_CI_IMAGE_BUILDER_ENV: "kaniko",
                constants.ODPM_KANIKO_EXECUTOR_MODE_ENV: "direct",
            },
        )
        docker = evaluate_docker_engine_check(ctx)
        compose = evaluate_compose_validate(ctx)
        self.assertEqual(docker.outcome, "skip")
        self.assertEqual(compose.outcome, "run")


class CiExplicitModeAllowlistTests(unittest.TestCase):
    def test_prepare_only_helpers(self):
        self.assertTrue(is_ci_prepare_only(OdpmCliArgs(skip_start=True)))
        self.assertTrue(is_ci_prepare_only(OdpmCliArgs(build_image=True)))
        self.assertTrue(is_ci_prepare_only(OdpmCliArgs(update_lock=True)))
        self.assertTrue(is_ci_prepare_only(OdpmCliArgs(sync_manifest_locks=True)))
        self.assertTrue(
            is_ci_prepare_only(OdpmCliArgs(init="https://example.com/repo.git"))
        )
        self.assertFalse(is_ci_prepare_only(OdpmCliArgs()))
        self.assertFalse(is_ci_prepare_only(OdpmCliArgs(plan=True)))

    def test_ci_kaniko_direct_update_lock_skips_daemon(self):
        args = OdpmCliArgs(update_lock=True)
        dotenv = {
            constants.ODPM_CI_IMAGE_BUILDER_ENV: "kaniko",
            constants.ODPM_KANIKO_EXECUTOR_MODE_ENV: "direct",
        }
        config = MagicMock()
        config.user_settings = MagicMock()
        config.user_settings.check_system = True
        config.policy = ScenarioPolicy.from_scenario(constants.CI_SCENARIO)
        config.arguments = args
        user_env = MagicMock()
        user_env.project_dotenv_dict.return_value = dict(dotenv)
        config.user_env = user_env
        policy = SystemCheckPolicy.from_config(config)
        self.assertTrue(policy.skip_docker_daemon)
        self.assertTrue(policy.skip_compose_cli_probe)
        self.assertTrue(policy.relaxed_file_system)
        self.assertTrue(policy.compose_validate)

        ctx = MagicMock()
        ctx.host_ctx = MagicMock()
        ctx.host_ctx.user_settings = config.user_settings
        ctx.host_ctx.policy = config.policy
        ctx.host_ctx.arguments = args
        ctx.host_ctx.user_env = user_env
        docker = evaluate_docker_engine_check(ctx)
        compose = evaluate_compose_validate(ctx)
        self.assertEqual(docker.outcome, "skip")
        self.assertEqual(compose.outcome, "run")

    def test_allowlist(self):
        allowed = (
            OdpmCliArgs(skip_start=True),
            OdpmCliArgs(build_image=True),
            OdpmCliArgs(plan=True),
            OdpmCliArgs(update_lock=True),
            OdpmCliArgs(sync_manifest_locks=True),
            OdpmCliArgs(init="https://example.com/repo.git"),
            OdpmCliArgs(version=True),
            OdpmCliArgs(command="plan"),
            OdpmCliArgs(command="database"),
            OdpmCliArgs(command="manifest"),
            OdpmCliArgs(database_subcommand="status"),
            OdpmCliArgs(manifest_subcommand="validate"),
        )
        for args in allowed:
            with self.subTest(args=args):
                self.assertTrue(cli_allows_ci_explicit_mode(args))
        self.assertFalse(cli_allows_ci_explicit_mode(OdpmCliArgs()))
        self.assertFalse(cli_allows_ci_explicit_mode(OdpmCliArgs(d="db", i=True)))


class MergedEnvironTests(unittest.TestCase):
    def test_process_env_wins_over_dotenv(self):
        merged = merged_environ_for_resolve(
            {constants.ODPM_CI_IMAGE_BUILDER_ENV: "kaniko"},
            process_environ={constants.ODPM_CI_IMAGE_BUILDER_ENV: "docker"},
        )
        self.assertEqual(merged[constants.ODPM_CI_IMAGE_BUILDER_ENV], "docker")

    def test_dotenv_used_when_process_unset(self):
        merged = merged_environ_for_resolve(
            {constants.ODPM_CI_IMAGE_BUILDER_ENV: "kaniko"},
            process_environ={},
        )
        self.assertEqual(merged[constants.ODPM_CI_IMAGE_BUILDER_ENV], "kaniko")


if __name__ == "__main__":
    unittest.main()
