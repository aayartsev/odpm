"""Tests for Docker Compose capability detection."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.check_system import SystemChecker
from dev_project.compose.compose_document import build_compose_document
from dev_project.docker_capabilities import (
    DockerCapabilities,
    detect_docker_capabilities,
    probe_compose_command_from_candidates,
    resolve_docker_capabilities,
)
from dev_project.errors import SystemCheckError
from tests.fixtures.compose.golden_scenario_env import make_golden_compose_env

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "docker"


class DetectDockerCapabilitiesTests(unittest.TestCase):
    def _read(self, name: str) -> str:
        return (FIXTURES / name).read_text(encoding="utf-8")

    def test_modern_compose_enables_yes_pull_policy_and_no_log_prefix(self):
        caps = detect_docker_capabilities(
            "docker compose",
            self._read("compose_up_help_modern.txt"),
            "Docker Compose version v2.24.5",
        )
        self.assertTrue(caps.supports_compose_up_yes)
        self.assertTrue(caps.supports_no_log_prefix)
        self.assertTrue(caps.supports_pull_policy_never)

    def test_legacy_compose_disables_yes_but_keeps_no_log_prefix(self):
        caps = detect_docker_capabilities(
            "docker compose",
            self._read("compose_up_help_legacy.txt"),
            "Docker Compose version v2.22.0",
        )
        self.assertFalse(caps.supports_compose_up_yes)
        self.assertTrue(caps.supports_no_log_prefix)
        self.assertTrue(caps.supports_pull_policy_never)

    def test_compose_up_yes_fallback_from_version_when_help_omits_flag(self):
        caps = detect_docker_capabilities(
            "docker compose",
            self._read("compose_up_help_legacy.txt"),
            "Docker Compose version v2.23.1",
        )
        self.assertTrue(caps.supports_compose_up_yes)

    def test_probe_selects_first_working_compose_command(self):
        def fake_run_checked(argv, **kwargs):
            result = MagicMock()
            if argv[-1] == "version":
                if argv[0] == "docker":
                    result.stdout = "Docker Compose version v2.24.0"
                else:
                    result.stdout = "unknown tool"
            else:
                result.stdout = (FIXTURES / "compose_up_help_modern.txt").read_text(
                    encoding="utf-8"
                )
            return result

        caps = probe_compose_command_from_candidates(
            constants.LIST_OF_DOCKER_COMPOSE_COMMANDS,
            run_checked=fake_run_checked,
        )
        self.assertIsNotNone(caps)
        assert caps is not None
        self.assertEqual(caps.compose_command, constants.DEFAULT_DOCKER_COMPOSE_COMMAND)
        self.assertTrue(caps.supports_compose_up_yes)


class ComposeDocumentPullPolicyTests(unittest.TestCase):
    def test_odoo_service_gets_pull_policy_never_when_supported(self):
        env = make_golden_compose_env(constants.DEVELOPER_SCENARIO)
        env.config.docker_capabilities = DockerCapabilities(
            compose_command=constants.DEFAULT_DOCKER_COMPOSE_COMMAND,
            compose_version_text="Docker Compose version v2.24.0",
            supports_no_log_prefix=True,
            supports_compose_up_yes=True,
            supports_pull_policy_never=True,
        )
        document = build_compose_document(env)
        self.assertEqual(document["services"]["odoo"]["pull_policy"], "never")

    def test_odoo_service_omits_pull_policy_when_unsupported(self):
        env = make_golden_compose_env(constants.DEVELOPER_SCENARIO)
        document = build_compose_document(env)
        self.assertNotIn("pull_policy", document["services"]["odoo"])


class ResolveDockerCapabilitiesTests(unittest.TestCase):
    def test_returns_cached_capabilities_without_subprocess(self):
        cached = DockerCapabilities(
            compose_command="docker compose",
            compose_version_text="Docker Compose version v2.24.0",
            supports_no_log_prefix=True,
            supports_compose_up_yes=False,
            supports_pull_policy_never=True,
        )
        config = MagicMock()
        config.docker_capabilities = cached
        with patch(
            "dev_project.docker_capabilities.probe_docker_capabilities"
        ) as mock_probe:
            resolved = resolve_docker_capabilities(config)
        self.assertIs(resolved, cached)
        mock_probe.assert_not_called()


class SystemCheckerComposeCapabilitiesTests(unittest.TestCase):
    def test_check_docker_compose_stores_capabilities(self):
        config = MagicMock()
        checker = SystemChecker(config, MagicMock())
        caps = DockerCapabilities(
            compose_command=constants.DEFAULT_DOCKER_COMPOSE_COMMAND,
            compose_version_text="Docker Compose version v2.24.0",
            supports_no_log_prefix=True,
            supports_compose_up_yes=True,
            supports_pull_policy_never=True,
        )
        with patch(
            "dev_project.check_system.probe_compose_command_from_candidates",
            return_value=caps,
        ):
            checker.check_docker_compose()
        self.assertEqual(config.docker_compose_command, caps.compose_command)
        self.assertEqual(config.no_log_prefix, caps.supports_no_log_prefix)
        self.assertEqual(config.docker_capabilities, caps)

    def test_check_docker_compose_raises_when_no_working_command(self):
        config = MagicMock()
        checker = SystemChecker(config, MagicMock())
        with patch(
            "dev_project.check_system.probe_compose_command_from_candidates",
            return_value=None,
        ):
            with self.assertRaises(SystemCheckError):
                checker.check_docker_compose()


if __name__ == "__main__":
    unittest.main()
