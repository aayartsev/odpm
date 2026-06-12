"""Tests for IDE-neutral debugger profile builder."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import MagicMock

from dev_project.project_env.debug_profile import (
    DEBUG_PROFILE_SCHEMA_VERSION,
    DebuggerProfile,
    DebuggerProfileBuilder,
)
from dev_project.project_env.types import MappedPath, SymlinksSources


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

        self.assertIn(os.path.abspath("/proj/sources/odoo"), local_roots)
        self.assertIn(os.path.abspath("/real/path/developing"), local_roots)
        self.assertNotIn(os.path.abspath("/proj/backups"), local_roots)

    def test_build_path_mappings_includes_project_symlink_aliases(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir:
            real_developing = os.path.join(project_dir, "sources", "acme-app")
            os.makedirs(real_developing)
            link_path = os.path.join(project_dir, "acme-app")
            os.symlink(real_developing, link_path)

            env = MagicMock()
            config = MagicMock()
            config.project_dir = project_dir
            config.dependencies_dir = os.path.join(project_dir, "dependencies")
            config.symlinks_sources = [
                SymlinksSources(source_path=real_developing, link_path=link_path)
            ]
            env.config = config
            env.user_env.backups = os.path.join(project_dir, "backups")
            env.user_env.debugger_port = 5678
            env.mapped_folders = [
                MappedPath(
                    local=real_developing,
                    docker="/home/odoo/extra-addons/acme-app",
                ),
            ]

            mappings = DebuggerProfileBuilder(env).build_path_mappings()
            local_roots = [mapping.local for mapping in mappings]

            self.assertIn(os.path.abspath(real_developing), local_roots)
            self.assertIn(os.path.abspath(link_path), local_roots)

    def test_build_path_mappings_discovers_existing_symlinks(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir:
            real_developing = os.path.join(project_dir, "sources", "app")
            os.makedirs(real_developing)
            link_path = os.path.join(project_dir, "app")
            os.symlink(real_developing, link_path)

            env = MagicMock()
            config = MagicMock()
            config.project_dir = project_dir
            config.dependencies_dir = os.path.join(project_dir, "dependencies")
            config.symlinks_sources = []
            env.config = config
            env.user_env.backups = os.path.join(project_dir, "backups")
            env.user_env.debugger_port = 5678
            env.mapped_folders = [
                MappedPath(
                    local=real_developing,
                    docker="/home/odoo/extra-addons/app",
                ),
            ]

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
                    "localRoot": os.path.abspath("/proj/sources/odoo"),
                    "remoteRoot": "/home/odoo/odoo",
                }
            ],
        )


if __name__ == "__main__":
    unittest.main()
