"""Tests for extras stamp and lock helpers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from dev_project.config.payload import compute_extras_stamp
from dev_project.inside_docker_app.extras_sync import (
    managed_distribution_names,
    read_extras_lock,
    write_extras_lock,
    write_extras_requirements_file,
)


class ExtrasSyncHelpersTests(unittest.TestCase):
    def test_managed_distribution_names_uses_canonical_names(self) -> None:
        names = managed_distribution_names(
            ["zeep[async]==4.2.1", "PyJWT==2.9.0", "zeep==4.2.1"]
        )
        self.assertEqual(names, ["pyjwt", "zeep"])

    def test_compute_extras_stamp_changes_when_requirements_change(self) -> None:
        first = compute_extras_stamp(["requests==2.31.0"])
        second = compute_extras_stamp(["requests==2.31.0", "debugpy==1.7.0"])
        self.assertNotEqual(first, second)

    def test_extras_lock_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = str(Path(tmp_dir) / ".extras.lock")
            write_extras_lock(
                path,
                stamp="abc123",
                distributions=["requests", "debugpy"],
            )
            state = read_extras_lock(path)
            self.assertIsNotNone(state)
            assert state is not None
            self.assertEqual(state.stamp, "abc123")
            self.assertEqual(state.distributions, ["debugpy", "requests"])

    def test_write_extras_requirements_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = str(Path(tmp_dir) / "extras.txt")
            write_extras_requirements_file(
                path,
                ["requests==2.31.0", "", "debugpy==1.7.0"],
            )
            content = Path(path).read_text(encoding="utf-8")
            self.assertEqual(
                content,
                "requests==2.31.0\ndebugpy==1.7.0\n",
            )


if __name__ == "__main__":
    unittest.main()
