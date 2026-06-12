"""Tests for IDE-neutral debugger profile builder."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.project_env.debug_profile import (
    DEBUG_PROFILE_SCHEMA_VERSION,
    DebuggerProfile,
    DebuggerProfileBuilder,
    debug_profile_path,
    write_debug_profile,
)
from dev_project.project_env.types import MappedPath, SymlinksSources

from tests.debug_profile_test_helpers import make_debugger_env_mock


class DebuggerProfileBuilderTests(unittest.TestCase):
    def _builder(self, *, mapped_folders: list[MappedPath]) -> DebuggerProfileBuilder:
        env = MagicMock()
        config = MagicMock()
        config.project_dir = "/proj"
        env.config = config
        env.user_env.backups = "/proj/backups"
        env.user_env.debugger_port = 5678
        env.mapped_folders = mapped_folders
        return DebuggerProfileBuilder(env)

    def test_build_path_mappings_uses_absolute_real_paths(self) -> None:
        builder = self._builder(
            mapped_folders=[
                MappedPath(local="/proj/sources/odoo", docker="/home/odoo/odoo"),
                MappedPath(local="/proj/backups", docker="/home/odoo/backups"),
                MappedPath(
                    local="/real/path/developing",
                    docker="/home/odoo/extra-addons/app",
                ),
            ]
        )

        mappings = builder.build_path_mappings()
        local_roots = [mapping.local for mapping in mappings]

        self.assertIn(os.path.realpath("/proj/sources/odoo"), local_roots)
        self.assertIn(os.path.realpath("/real/path/developing"), local_roots)
        self.assertNotIn(os.path.realpath("/proj/backups"), local_roots)

    def test_build_path_mappings_includes_project_symlink_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir:
            real_developing = os.path.join(project_dir, "sources", "acme-app")
            os.makedirs(real_developing)
            link_path = os.path.join(project_dir, "acme-app")
            os.symlink(real_developing, link_path)

            env = make_debugger_env_mock(
                project_dir=project_dir,
                symlinks_sources=[
                    SymlinksSources(source_path=real_developing, link_path=link_path)
                ],
                mapped_folders=[
                    MappedPath(
                        local=real_developing,
                        docker="/home/odoo/extra-addons/acme-app",
                    ),
                ],
            )

            mappings = DebuggerProfileBuilder(env).build_path_mappings()
            local_roots = [mapping.local for mapping in mappings]

            self.assertIn(os.path.realpath(real_developing), local_roots)
            self.assertIn(os.path.abspath(link_path), local_roots)

    def test_build_path_mappings_discovers_existing_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir:
            real_developing = os.path.join(project_dir, "sources", "app")
            os.makedirs(real_developing)
            link_path = os.path.join(project_dir, "app")
            os.symlink(real_developing, link_path)

            env = make_debugger_env_mock(
                project_dir=project_dir,
                mapped_folders=[
                    MappedPath(
                        local=real_developing,
                        docker="/home/odoo/extra-addons/app",
                    ),
                ],
            )

            mappings = DebuggerProfileBuilder(env).build_path_mappings()
            local_roots = [mapping.local for mapping in mappings]

            self.assertIn(os.path.abspath(link_path), local_roots)

    def test_build_returns_schema_v1_profile(self) -> None:
        builder = self._builder(
            mapped_folders=[
                MappedPath(local="/proj/sources/odoo", docker="/home/odoo/odoo"),
            ]
        )

        profile = builder.build()
        payload = profile.to_dict()

        self.assertEqual(payload["schema_version"], DEBUG_PROFILE_SCHEMA_VERSION)
        self.assertEqual(payload["debugger"]["protocol"], "debugpy")
        self.assertEqual(payload["debugger"]["port"], 5678)
        self.assertEqual(
            DebuggerProfile.from_dict(payload).to_dict(),
            payload,
        )

    def test_to_vscode_path_mappings_uses_local_root_keys(self) -> None:
        builder = self._builder(
            mapped_folders=[
                MappedPath(local="/proj/sources/odoo", docker="/home/odoo/odoo"),
            ]
        )

        profile = builder.build()
        vscode_mappings = profile.to_vscode_path_mappings()

        self.assertEqual(
            vscode_mappings,
            [
                {
                    "localRoot": os.path.realpath("/proj/sources/odoo"),
                    "remoteRoot": "/home/odoo/odoo",
                }
            ],
        )

    def test_from_dict_rejects_unsupported_schema_version(self) -> None:
        with self.assertRaises(ValueError) as ctx:
            DebuggerProfile.from_dict({"schema_version": 99, "debugger": {}})
        self.assertIn("schema_version", str(ctx.exception))

    def test_write_debug_profile_writes_runtime_json(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir:
            odoo_src = os.path.join(project_dir, "sources", "odoo")
            os.makedirs(odoo_src)

            env = make_debugger_env_mock(
                project_dir=project_dir,
                mapped_folders=[
                    MappedPath(local=odoo_src, docker="/home/odoo/odoo"),
                ],
            )

            written_path = write_debug_profile(env)

            self.assertEqual(
                written_path,
                debug_profile_path(project_dir),
            )
            self.assertTrue(os.path.isfile(written_path))
            with open(written_path, encoding="utf-8") as profile_file:
                payload = json.load(profile_file)
            self.assertEqual(payload["schema_version"], DEBUG_PROFILE_SCHEMA_VERSION)
            self.assertEqual(payload["debugger"]["port"], 5678)
            local_roots = [item["local"] for item in payload["path_mappings"]]
            self.assertEqual(local_roots, [os.path.realpath(odoo_src)])

            gitignore_path = os.path.join(
                project_dir, constants.ODPM_RUNTIME_DIR_REL_PATH, ".gitignore"
            )
            self.assertTrue(os.path.isfile(gitignore_path))


if __name__ == "__main__":
    unittest.main()
