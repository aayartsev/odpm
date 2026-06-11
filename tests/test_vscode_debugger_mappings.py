"""Tests for VS Code debugger pathMappings generation."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.project_env.services import VscodeConfigurator
from dev_project.project_env.types import MappedPath, SymlinksSources


class VscodeDebuggerMappingsTests(unittest.TestCase):
    def _configurator(self, *, mapped_folders: list[MappedPath]) -> VscodeConfigurator:
        env = MagicMock()
        config = MagicMock()
        config.project_dir = "/proj"
        config.debugger_path_mappings = []
        env.config = config
        env.user_env.backups = "/proj/backups"
        env.mapped_folders = mapped_folders
        return VscodeConfigurator(env)

    def test_build_debugger_path_mappings_uses_absolute_real_paths(self) -> None:
        configurator = self._configurator(
            mapped_folders=[
                MappedPath(local="/proj/sources/odoo", docker="/home/odoo/odoo"),
                MappedPath(local="/proj/backups", docker="/home/odoo/backups"),
                MappedPath(
                    local="/real/path/developing",
                    docker="/home/odoo/extra-addons/app",
                ),
            ]
        )

        mappings = configurator.build_debugger_path_mappings()

        local_roots = [record["localRoot"] for record in mappings]
        self.assertIn(os.path.abspath("/proj/sources/odoo"), local_roots)
        self.assertIn(os.path.abspath("/real/path/developing"), local_roots)
        self.assertNotIn(os.path.abspath("/proj/backups"), local_roots)

    def test_update_vscode_debugger_launcher_writes_real_local_roots(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir:
            odoo_src = os.path.join(project_dir, "sources", "odoo")
            os.makedirs(odoo_src)
            backups = os.path.join(project_dir, "backups")
            os.makedirs(backups)

            env = MagicMock()
            config = MagicMock()
            config.project_dir = project_dir
            config.debugger_path_mappings = []
            env.config = config
            env.user_env.backups = backups
            env.user_env.debugger_port = 5678
            env.mapped_folders = [
                MappedPath(local=odoo_src, docker="/home/odoo/odoo"),
                MappedPath(local=backups, docker="/home/odoo/backups"),
            ]

            VscodeConfigurator(env).update_vscode_debugger_launcher()

            launch_json = os.path.join(project_dir, ".vscode", "launch.json")
            with open(launch_json, encoding="utf-8") as launch_file:
                payload = json.load(launch_file)
            odoo_unit = next(
                unit
                for unit in payload["configurations"]
                if unit["name"] == constants.DEBUGGER_UNIT_NAME
            )
            local_roots = [
                mapping["localRoot"] for mapping in odoo_unit["pathMappings"]
            ]
            self.assertEqual(local_roots, [os.path.abspath(odoo_src)])

    def test_build_debugger_path_mappings_includes_project_symlink_aliases(self) -> None:
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
            env.mapped_folders = [
                MappedPath(
                    local=real_developing,
                    docker="/home/odoo/extra-addons/acme-app",
                ),
            ]

            mappings = VscodeConfigurator(env).build_debugger_path_mappings()
            local_roots = [record["localRoot"] for record in mappings]

            self.assertIn(os.path.abspath(real_developing), local_roots)
            self.assertIn(os.path.abspath(link_path), local_roots)

    def test_build_debugger_path_mappings_discovers_existing_symlinks(self) -> None:
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
            env.mapped_folders = [
                MappedPath(
                    local=real_developing,
                    docker="/home/odoo/extra-addons/app",
                ),
            ]

            mappings = VscodeConfigurator(env).build_debugger_path_mappings()
            local_roots = [record["localRoot"] for record in mappings]

            self.assertIn(os.path.abspath(link_path), local_roots)

    def test_update_vscode_debugger_launcher_writes_symlink_local_roots(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir:
            real_developing = os.path.join(project_dir, "sources", "app")
            os.makedirs(real_developing)
            link_path = os.path.join(project_dir, "app")
            os.symlink(real_developing, link_path)

            env = MagicMock()
            config = MagicMock()
            config.project_dir = project_dir
            config.dependencies_dir = os.path.join(project_dir, "dependencies")
            config.debugger_path_mappings = []
            config.symlinks_sources = [
                SymlinksSources(source_path=real_developing, link_path=link_path)
            ]
            env.config = config
            env.user_env.backups = os.path.join(project_dir, "backups")
            env.user_env.debugger_port = 5678
            env.mapped_folders = [
                MappedPath(
                    local=real_developing,
                    docker="/home/odoo/extra-addons/app",
                ),
            ]

            VscodeConfigurator(env).update_vscode_debugger_launcher()

            launch_json = os.path.join(project_dir, ".vscode", "launch.json")
            with open(launch_json, encoding="utf-8") as launch_file:
                payload = json.load(launch_file)
            odoo_unit = next(
                unit
                for unit in payload["configurations"]
                if unit["name"] == constants.DEBUGGER_UNIT_NAME
            )
            local_roots = [
                mapping["localRoot"] for mapping in odoo_unit["pathMappings"]
            ]
            self.assertIn(os.path.abspath(real_developing), local_roots)
            self.assertIn(os.path.abspath(link_path), local_roots)


if __name__ == "__main__":
    unittest.main()
