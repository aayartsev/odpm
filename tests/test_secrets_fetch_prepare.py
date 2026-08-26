"""Prepare-step and coordinator tests for secrets.fetch."""

from __future__ import annotations

import tempfile
import unittest
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.prepare import make_prepare_context
from dev_project.prepare.steps_secrets import evaluate_secrets_fetch, exec_secrets_fetch
from dev_project.project_env.secrets import read_secrets_source, write_secrets_source
from dev_project.scenario_policy import ScenarioPolicy
from dev_project.secrets_providers.fetch import ensure_secrets_source
from dev_project.secrets_providers.registry import (
    clear_secrets_providers_for_tests,
    register_secrets_provider,
)
from dev_project.secrets_providers.session import SecretsFetchSession


class _CountingProvider:
    name = "fake"

    def __init__(self) -> None:
        self.calls = 0

    def fetch(self, **_kwargs):
        self.calls += 1
        return {"k": "v"}


def _minimal_raw(**extra) -> dict:
    payload = {
        "manifest_schema": 2,
        "requires_odpm": "4.7.0",
        "platform": {"git": "https://github.com/odoo/odoo.git 19.0"},
        "python": "3.12",
        "distro": {"name": "debian", "version": "13"},
        "postgres": "15",
    }
    payload.update(extra)
    return payload


class SecretsFetchCoordinatorTests(unittest.TestCase):
    def tearDown(self) -> None:
        clear_secrets_providers_for_tests()

    def test_two_ensure_calls_fetch_once(self):
        provider = _CountingProvider()
        register_secrets_provider(provider)
        session = SecretsFetchSession()
        with tempfile.TemporaryDirectory() as project_dir:
            kwargs = dict(
                project_dir=project_dir,
                arguments=OdpmCliArgs(),
                environ={constants.ODPM_SECRETS_PROVIDER_ENV: "fake"},
                raw_manifest={},
                session=session,
                active_scenario=constants.DEVELOPER_SCENARIO,
                phase="prepare",
            )
            first = ensure_secrets_source(**kwargs)
            second = ensure_secrets_source(**kwargs)
            self.assertTrue(first.did_fetch)
            self.assertFalse(second.did_fetch)
            self.assertEqual(provider.calls, 1)
            self.assertEqual(read_secrets_source(project_dir), {"k": "v"})

    def test_early_skips_remote_without_secret_refs(self):
        provider = _CountingProvider()
        register_secrets_provider(provider)
        session = SecretsFetchSession()
        with tempfile.TemporaryDirectory() as project_dir:
            result = ensure_secrets_source(
                project_dir=project_dir,
                arguments=OdpmCliArgs(),
                environ={constants.ODPM_SECRETS_PROVIDER_ENV: "fake"},
                raw_manifest=_minimal_raw(
                    secrets={"provider": {"type": "fake"}},
                ),
                session=session,
                active_scenario=constants.DEVELOPER_SCENARIO,
                phase="early",
            )
            self.assertTrue(result.skipped)
            self.assertEqual(provider.calls, 0)
            self.assertFalse(session.fetched)

    def test_early_fetches_remote_when_secret_refs_present(self):
        provider = _CountingProvider()
        register_secrets_provider(provider)
        session = SecretsFetchSession()
        raw = _minimal_raw(
            secrets={"provider": {"type": "fake"}},
            services={
                "armtek": {
                    "image": "x",
                    "environment": {"T": "${@secret:k}"},
                }
            },
        )
        with tempfile.TemporaryDirectory() as project_dir:
            result = ensure_secrets_source(
                project_dir=project_dir,
                arguments=OdpmCliArgs(),
                environ={constants.ODPM_SECRETS_PROVIDER_ENV: "fake"},
                raw_manifest=raw,
                session=session,
                active_scenario=constants.DEVELOPER_SCENARIO,
                phase="early",
            )
            self.assertTrue(result.did_fetch)
            self.assertEqual(provider.calls, 1)
            prepare = ensure_secrets_source(
                project_dir=project_dir,
                arguments=OdpmCliArgs(),
                environ={constants.ODPM_SECRETS_PROVIDER_ENV: "fake"},
                raw_manifest=raw,
                session=session,
                active_scenario=constants.DEVELOPER_SCENARIO,
                phase="prepare",
            )
            self.assertFalse(prepare.did_fetch)
            self.assertEqual(provider.calls, 1)

    def test_plan_without_secret_refs_does_not_call_urlopen(self):
        session = SecretsFetchSession()
        raw = _minimal_raw(
            secrets={
                "provider": {
                    "type": "infisical",
                    "project_id": "p",
                    "environment_slug": "dev",
                }
            },
        )
        with tempfile.TemporaryDirectory() as project_dir:
            with patch(
                "dev_project.secrets_providers.infisical_client.urllib.request.urlopen"
            ) as mock_urlopen:
                result = ensure_secrets_source(
                    project_dir=project_dir,
                    arguments=OdpmCliArgs(plan=True),
                    environ={},
                    raw_manifest=raw,
                    session=session,
                    active_scenario=constants.DEVELOPER_SCENARIO,
                    phase="early",
                )
            self.assertTrue(result.skipped)
            mock_urlopen.assert_not_called()


class SecretsFetchPrepareStepTests(unittest.TestCase):
    def _ctx(self, project_dir: str, args: OdpmCliArgs, scenario: str = "developer"):
        config = MagicMock()
        config.project_dir = project_dir
        config.policy = ScenarioPolicy.from_scenario(scenario)
        config.arguments = args
        config.secrets_fetch_session = SecretsFetchSession()
        config.user_env.project_dotenv_dict.return_value = {}
        config.user_env.odpm_scenario = scenario
        config.bootstrap.manifest_view = None
        return make_prepare_context(config, MagicMock(), MagicMock(), args)

    def test_file_without_flag_skips(self):
        with tempfile.TemporaryDirectory() as project_dir:
            step = evaluate_secrets_fetch(self._ctx(project_dir, OdpmCliArgs()))
            self.assertEqual(step.id, "secrets.fetch")
            self.assertEqual(step.outcome, "skip")
            self.assertNotIn("sk_live", step.description)
            self.assertNotIn("sk_live", step.reason)

    def test_file_with_secrets_file_after_session_fetched_skips(self):
        with tempfile.TemporaryDirectory() as project_dir:
            args = OdpmCliArgs(secrets_file="/tmp/x.json")
            ctx = self._ctx(project_dir, args)
            ctx.ports.bootstrap.config.secrets_fetch_session.fetched = True
            ctx.ports.bootstrap.config.secrets_fetch_session.provider_name = "file"
            step = evaluate_secrets_fetch(ctx)
            self.assertEqual(step.outcome, "skip")

    def test_remote_update_when_session_empty(self):
        with tempfile.TemporaryDirectory() as project_dir:
            ctx = self._ctx(
                project_dir,
                OdpmCliArgs(secrets_provider="fake"),
            )
            step = evaluate_secrets_fetch(ctx)
            self.assertEqual(step.outcome, "update")
            self.assertIn("fake", step.description)

    def test_exec_does_not_put_values_in_plan_text(self):
        provider = _CountingProvider()
        register_secrets_provider(provider)
        self.addCleanup(clear_secrets_providers_for_tests)
        with tempfile.TemporaryDirectory() as project_dir:
            write_secrets_source(project_dir, {"secret": "must-not-appear"})
            ctx = self._ctx(
                project_dir, OdpmCliArgs(secrets_provider="fake")
            )
            exec_secrets_fetch(ctx)
            step = evaluate_secrets_fetch(ctx)
            blob = f"{step.description} {step.reason}"
            self.assertNotIn("must-not-appear", blob)
            self.assertEqual(step.outcome, "noop")


if __name__ == "__main__":
    unittest.main()
