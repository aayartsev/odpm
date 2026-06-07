"""Tests for VS Code debugger pathMappings generation."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.project_env.templates import ProjectTemplates
from dev_project.project_env.types import MappedPath


class VscodeDebuggerMappingsTests(unittest.TestCase):
    def _templates(self, *, mapped_folders: list[MappedPath]) -> ProjectTemplates:
        env = MagicMock()
        config = MagicMock()
        config.project_dir = "/proj"
        config.debugger_path_mappings = []
        env.config = config
        env.user_env.backups = "/proj/backups"
        env.mapped_folders = mapped_folders
        return ProjectTemplates(env)

    def test_build_debugger_path_mappings_uses_absolute_real_paths(self) -> None:
        templates = self._templates(
            mapped_folders=[
                MappedPath(local="/proj/sources/odoo", docker="/home/odoo/odoo"),
                MappedPath(local="/proj/backups", docker="/home/odoo/backups"),
                MappedPath(
                    local="/real/path/developing",
                    docker="/home/odoo/extra-addons/app",
                ),
            ]
        )

        mappings = templates._build_debugger_path_mappings()

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

            ProjectTemplates(env).update_vscode_debugger_launcher()

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


if __name__ == "__main__":
    unittest.main()
