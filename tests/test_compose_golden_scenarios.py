"""Golden compose YAML snapshots per scenario (D5-2)."""

from __future__ import annotations

import unittest
from pathlib import Path

from dev_project import constants
from dev_project.compose.validate import validate_compose_document
from dev_project.yaml import load_document
from tests.fixtures.compose.golden_scenario_env import render_golden_compose_yaml

GOLDEN_DIR = Path(__file__).resolve().parent / "fixtures" / "compose" / "golden"


class ComposeGoldenScenarioTests(unittest.TestCase):
    def _assert_matches_golden(self, scenario: str) -> None:
        golden_path = GOLDEN_DIR / f"{scenario}.yml"
        self.assertTrue(golden_path.is_file(), msg=f"missing golden file {golden_path}")
        expected = golden_path.read_text(encoding="utf-8")
        actual = render_golden_compose_yaml(scenario)
        self.assertEqual(actual, expected)
        document = load_document(actual)
        validate_compose_document(document)

    def test_developer_compose_matches_golden_snapshot(self):
        self._assert_matches_golden(constants.DEVELOPER_SCENARIO)

    def test_server_compose_matches_golden_snapshot(self):
        self._assert_matches_golden(constants.SERVER_SCENARIO)

    def test_ci_compose_matches_golden_snapshot(self):
        self._assert_matches_golden(constants.CI_SCENARIO)


if __name__ == "__main__":
    unittest.main()
