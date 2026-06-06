"""Tests for runtime config preview used in plan evaluation and diffs."""

import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.plan_runtime_preview import (
    clear_runtime_config_preview_cache,
    normalize_runtime_config_text,
    preview_runtime_config_text,
    strip_plan_only_arguments,
)


class PlanRuntimePreviewTests(unittest.TestCase):
    def test_strip_plan_only_arguments(self):
        arguments = {
            "plan": True,
            "plan_no_docker": False,
            "plan_show_diff": True,
            "branch": "dev",
        }
        self.assertEqual(
            strip_plan_only_arguments(arguments),
            {"branch": "dev"},
        )

    def test_normalize_runtime_config_text_strips_plan_flags_and_formats(self):
        raw = json.dumps(
            {
                "schema_version": 1,
                "arguments": {
                    "plan": True,
                    "plan_show_diff": True,
                    "branch": "dev",
                },
            }
        )
        normalized = normalize_runtime_config_text(raw)
        payload = json.loads(normalized)
        self.assertNotIn("plan", payload["arguments"])
        self.assertNotIn("plan_show_diff", payload["arguments"])
        self.assertEqual(payload["arguments"]["branch"], "dev")
        self.assertIn("\n", normalized)

    @patch(
        "dev_project.plan_runtime_preview.runtime_config_payload_from_config",
        return_value={"arguments": {"branch": "dev"}, "schema_version": 1},
    )
    @patch("dev_project.plan_compose_preview.preview_compose_service")
    def test_preview_runtime_config_text_uses_compose_service_path(
        self, mock_preview, _mock_payload
    ):
        config = MagicMock()
        config.arguments = Namespace(plan=True, branch="dev")
        text = preview_runtime_config_text(config)
        mock_preview.assert_called_once_with(config)
        self.assertIsNotNone(text)
        payload = json.loads(text or "{}")
        self.assertEqual(payload["arguments"]["branch"], "dev")

    @patch(
        "dev_project.plan_runtime_preview.runtime_config_payload_from_config",
        return_value={"arguments": {"branch": "dev"}, "schema_version": 1},
    )
    @patch("dev_project.plan_compose_preview.preview_compose_service")
    def test_preview_runtime_config_text_is_cached_per_plan_build(
        self, mock_preview, _mock_payload
    ):
        config = MagicMock()
        config.arguments = Namespace(branch="dev")
        clear_runtime_config_preview_cache(config)
        first = preview_runtime_config_text(config)
        second = preview_runtime_config_text(config)
        self.assertEqual(first, second)
        mock_preview.assert_called_once_with(config)


if __name__ == "__main__":
    unittest.main()
