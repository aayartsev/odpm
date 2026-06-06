import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.git.deps_lock import (
    DEPS_LOCK_SCHEMA_VERSION,
    DepsLock,
    LockEntry,
    apply_lock_entry_to_link,
    deps_lock_path,
    entry_for_url,
    is_git_repository,
    load_deps_lock,
    normalize_repo_url,
    resolve_lock_commit,
    save_deps_lock,
    snapshot_commit_for_path,
)


class NormalizeRepoUrlTests(unittest.TestCase):
    def test_strips_git_suffix_and_whitespace(self):
        self.assertEqual(
            normalize_repo_url("  https://github.com/acme/demo.git  "),
            "https://github.com/acme/demo",
        )

    def test_uses_first_token(self):
        self.assertEqual(
            normalize_repo_url("https://github.com/acme/demo.git 17.0"),
            "https://github.com/acme/demo",
        )


class LockEntryTests(unittest.TestCase):
    def test_from_dict_requires_url_and_commit(self):
        with self.assertRaises(ValueError):
            LockEntry.from_dict({"url": "https://example.com/repo"})

    def test_from_dict_rejects_invalid_commit(self):
        with self.assertRaises(ValueError):
            LockEntry.from_dict(
                {"url": "https://example.com/repo", "commit": "not-a-sha"}
            )

    def test_roundtrip_with_optional_branch(self):
        entry = LockEntry(
            url="https://github.com/acme/demo",
            commit="deadbeef0123456789abcdef0123456789abcdef",
            branch="17.0",
        )
        restored = LockEntry.from_dict(entry.to_dict())
        self.assertEqual(restored.url, entry.url)
        self.assertEqual(restored.commit, entry.commit)
        self.assertEqual(restored.branch, entry.branch)


class DepsLockTests(unittest.TestCase):
    def _sample_lock(self) -> DepsLock:
        return DepsLock(
            generated_at="2026-06-05T12:00:00+00:00",
            platform=LockEntry(
                url="https://github.com/odoo/odoo",
                commit="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                branch="19.0",
            ),
            dependencies=[
                LockEntry(
                    url="https://github.com/OCA/partner-contact",
                    commit="bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
                )
            ],
        )

    def test_from_dict_rejects_unsupported_schema(self):
        with self.assertRaises(ValueError):
            DepsLock.from_dict({"schema_version": 99, "platform": {}})

    def test_load_save_roundtrip(self):
        with tempfile.TemporaryDirectory() as project_dir:
            path = deps_lock_path(project_dir)
            lock = self._sample_lock()
            save_deps_lock(path, lock)
            loaded = load_deps_lock(path)
            self.assertIsNotNone(loaded)
            assert loaded is not None
            self.assertEqual(loaded.schema_version, DEPS_LOCK_SCHEMA_VERSION)
            self.assertEqual(loaded.platform.url, lock.platform.url)
            self.assertEqual(loaded.platform.commit, lock.platform.commit)
            self.assertEqual(len(loaded.dependencies), 1)
            self.assertEqual(loaded.dependencies[0].commit, lock.dependencies[0].commit)

    def test_load_missing_file_returns_none(self):
        with tempfile.TemporaryDirectory() as project_dir:
            self.assertIsNone(load_deps_lock(deps_lock_path(project_dir)))

    def test_entry_for_url_matches_platform_and_dependencies(self):
        lock = self._sample_lock()
        self.assertIsNotNone(entry_for_url(lock, "https://github.com/odoo/odoo.git"))
        self.assertIsNotNone(
            entry_for_url(lock, "https://github.com/OCA/partner-contact")
        )
        self.assertIsNone(entry_for_url(lock, "https://github.com/other/repo"))

    def test_deps_lock_rel_path_under_odpm(self):
        self.assertTrue(constants.DEPS_LOCK_REL_PATH.endswith("deps.lock.json"))
        self.assertIn(".odpm", constants.DEPS_LOCK_REL_PATH)


class SnapshotCommitTests(unittest.TestCase):
    def test_snapshot_commit_is_stable_for_same_tree(self):
        with tempfile.TemporaryDirectory() as project_dir:
            odoo_dir = os.path.join(project_dir, "odoo")
            os.makedirs(odoo_dir)
            Path(odoo_dir, "release.py").write_text(
                "version_info = (19, 0, 0, 'final', 0)\n", encoding="utf-8"
            )
            Path(project_dir, "odoo-bin").write_text("#!/bin/sh\n", encoding="utf-8")

            first = snapshot_commit_for_path(project_dir)
            second = snapshot_commit_for_path(project_dir)
            self.assertEqual(first, second)
            self.assertRegex(first, r"^[0-9a-f]{40}$")

    def test_resolve_lock_commit_uses_file_snapshot(self):
        with tempfile.TemporaryDirectory() as project_dir:
            odoo_dir = os.path.join(project_dir, "odoo")
            os.makedirs(odoo_dir)
            (Path(odoo_dir) / "release.py").write_text("x", encoding="utf-8")
            (Path(project_dir) / "odoo-bin").write_text("y", encoding="utf-8")

            link = type("Link", (), {})()
            link.commit_explicit = False
            link.commit = ""
            link.project_path = project_dir
            link.project_string = f"file://{project_dir}"
            link.link_type = constants.GITLINK_TYPE_FILE
            link.get_project_path = lambda: project_dir
            link.resolve_head_sha = MagicMock(side_effect=AssertionError("must not call git"))

            self.assertEqual(
                resolve_lock_commit(link),
                snapshot_commit_for_path(project_dir),
            )

    def test_is_git_repository_false_for_plain_directory(self):
        with tempfile.TemporaryDirectory() as project_dir:
            self.assertFalse(is_git_repository(project_dir))


class ApplyLockEntryTests(unittest.TestCase):
    def test_apply_lock_entry_sets_commit_and_branch(self):
        link = type("Link", (), {})()
        link.commit = ""
        link.commit_explicit = False
        link.branch = ""
        link.branch_explicit = False

        entry = LockEntry(
            url="https://github.com/acme/demo",
            commit="deadbeef0123456789abcdef0123456789abcdef",
            branch="17.0",
        )
        apply_lock_entry_to_link(link, entry)

        self.assertEqual(link.commit, entry.commit)
        self.assertTrue(link.commit_explicit)
        self.assertEqual(link.branch, "17.0")
        self.assertTrue(link.branch_explicit)


class SaveDepsLockTests(unittest.TestCase):
    def test_save_writes_valid_json(self):
        with tempfile.TemporaryDirectory() as project_dir:
            path = os.path.join(project_dir, ".odpm", "deps.lock.json")
            lock = DepsLock(
                platform=LockEntry(
                    url="https://github.com/odoo/odoo",
                    commit="aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                ),
            )
            save_deps_lock(path, lock)
            with open(path, encoding="utf-8") as reader:
                data = json.load(reader)
            self.assertEqual(data["schema_version"], DEPS_LOCK_SCHEMA_VERSION)
            self.assertIn("generated_at", data)
            self.assertIn("platform", data)
            self.assertIn("dependencies", data)


if __name__ == "__main__":
    unittest.main()
