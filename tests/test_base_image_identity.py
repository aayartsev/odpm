import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.project_env.base_image_identity import (
    base_image_identity_matches,
    base_image_identity_path,
    ensure_base_image_identity_gitignore,
    expected_base_image_identity,
    read_base_image_identity,
    write_base_image_identity,
)
from dev_project.scenario_policy import ScenarioPolicy


class BaseImageIdentityTests(unittest.TestCase):
    def _config(self, project_dir: str, scenario: str) -> MagicMock:
        config = MagicMock()
        config.project_dir = project_dir
        config.policy = ScenarioPolicy.from_scenario(scenario)
        return config

    def test_expected_identity_developer_uses_host(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = self._config(project_dir, constants.DEVELOPER_SCENARIO)
            identity = expected_base_image_identity(config)
            self.assertEqual(identity["user"], constants.HOST_USER)
            self.assertEqual(identity["uid"], str(constants.HOST_USER_UID))
            self.assertEqual(identity["gid"], str(constants.HOST_USER_GID))

    def test_expected_identity_ci_uses_container(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = self._config(project_dir, constants.CI_SCENARIO)
            identity = expected_base_image_identity(config)
            self.assertEqual(identity["user"], constants.CONTAINER_USER)
            self.assertEqual(identity["uid"], constants.CONTAINER_USER_UID)
            self.assertEqual(identity["gid"], constants.CONTAINER_USER_GID)
            self.assertEqual(identity["base_image_profile"], "ci")

    def test_expected_identity_includes_dockerfile_sha256(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = self._config(project_dir, constants.DEVELOPER_SCENARIO)
            dockerfile = os.path.join(project_dir, constants.DOCKERFILE)
            with open(dockerfile, "w", encoding="utf-8") as writer:
                writer.write("FROM python:3.12\n")
            identity = expected_base_image_identity(config)
            self.assertTrue(identity["dockerfile_sha256"])
            self.assertEqual(identity["base_image_profile"], "full")

    def test_write_and_read_round_trip(self):
        with tempfile.TemporaryDirectory() as project_dir:
            identity = {
                "user": "alice",
                "uid": "1001",
                "gid": "1001",
                "base_image_profile": "full",
                "dockerfile_sha256": "abc",
            }
            write_base_image_identity(project_dir, identity)
            path = base_image_identity_path(project_dir)
            self.assertTrue(os.path.isfile(path))
            self.assertEqual(read_base_image_identity(project_dir), identity)

    def test_read_returns_none_for_missing_or_invalid_stamp(self):
        with tempfile.TemporaryDirectory() as project_dir:
            self.assertIsNone(read_base_image_identity(project_dir))
            path = base_image_identity_path(project_dir)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as writer:
                json.dump({"user": "odoo"}, writer)
            self.assertIsNone(read_base_image_identity(project_dir))

    def test_identity_matches_when_stamp_equals_policy(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = self._config(project_dir, constants.SERVER_SCENARIO)
            write_base_image_identity(
                project_dir, expected_base_image_identity(config)
            )
            self.assertTrue(base_image_identity_matches(config))

    def test_write_creates_odpm_gitignore_entry(self):
        with tempfile.TemporaryDirectory() as project_dir:
            write_base_image_identity(
                project_dir, {"user": "alice", "uid": "1001", "gid": "1001"}
            )
            gitignore_path = os.path.join(project_dir, ".odpm", ".gitignore")
            self.assertTrue(os.path.isfile(gitignore_path))
            self.assertIn("base_image_identity.json", Path(gitignore_path).read_text())

    def test_ensure_gitignore_appends_without_duplicating(self):
        with tempfile.TemporaryDirectory() as project_dir:
            odpm_dir = os.path.join(project_dir, ".odpm")
            os.makedirs(odpm_dir, exist_ok=True)
            gitignore_path = os.path.join(odpm_dir, ".gitignore")
            Path(gitignore_path).write_text("runtime/\n", encoding="utf-8")
            ensure_base_image_identity_gitignore(project_dir)
            content = Path(gitignore_path).read_text(encoding="utf-8")
            self.assertIn("runtime/", content)
            self.assertEqual(content.count("base_image_identity.json"), 1)
            ensure_base_image_identity_gitignore(project_dir)
            self.assertEqual(
                Path(gitignore_path).read_text(encoding="utf-8").count(
                    "base_image_identity.json"
                ),
                1,
            )

    def test_identity_mismatch_when_profile_changes(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = self._config(project_dir, constants.SERVER_SCENARIO)
            stamp = expected_base_image_identity(config)
            stamp = {**stamp, "base_image_profile": "full"}
            write_base_image_identity(project_dir, stamp)
            self.assertFalse(base_image_identity_matches(config))


if __name__ == "__main__":
    unittest.main()
