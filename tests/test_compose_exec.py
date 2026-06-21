"""Tests for docker compose exec helpers."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from dev_project.database.compose_exec import compose_up_service_detached


class ComposeUpServiceDetachedTests(unittest.TestCase):
    @patch("dev_project.database.compose_exec.run_checked")
    def test_passes_yes_for_non_interactive_detached_up(self, mock_run: MagicMock) -> None:
        config = MagicMock()
        config.project_dir = "/tmp/project"
        config.docker_compose_command = "docker compose"
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")

        compose_up_service_detached(config, "db-dev")

        mock_run.assert_called_once()
        self.assertEqual(
            mock_run.call_args.args[0],
            ["docker", "compose", "up", "-d", "-y", "db-dev"],
        )
        self.assertEqual(mock_run.call_args.kwargs["cwd"], "/tmp/project")


if __name__ == "__main__":
    unittest.main()
