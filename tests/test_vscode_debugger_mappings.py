"""Tests for VS Code launch.json generation on top of DebuggerProfile."""

from __future__ import annotations

import json
import os
import tempfile
import unittest

from dev_project import constants
from dev_project.project_env.debug_profile import DebuggerProfileBuilder
from dev_project.project_env.services import VscodeConfigurator
from dev_project.project_env.types import MappedPath, SymlinksSources

from tests.debug_profile_test_helpers import make_debugger_env_mock


class VscodeDebuggerMappingsTests(unittest.TestCase):
    def test_build_debugger_path_mappings_matches_debugger_profile(self) -> None:
        env = make_debugger_env_mock(
            project_dir="/proj",
            mapped_folders=[
                MappedPath(local="/proj/sources/odoo", docker="/home/odoo/odoo"),
                MappedPath(local="/proj/backups", docker="/home/odoo/backups"),
            ],
        )

        profile = DebuggerProfileBuilder(env).build()
        mappings = VscodeConfigurator(env).build_debugger_path_mappings()

        self.assertEqual(mappings, profile.to_vscode_path_mappings())

    def test_update_vscode_debugger_launcher_writes_profile_connection(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir:
            odoo_src = os.path.join(project_dir, "sources", "odoo")
            os.makedirs(odoo_src)
            backups = os.path.join(project_dir, "backups")
            os.makedirs(backups)

            env = make_debugger_env_mock(
                project_dir=project_dir,
                mapped_folders=[
                    MappedPath(local=odoo_src, docker="/home/odoo/odoo"),
                    MappedPath(local=backups, docker="/home/odoo/backups"),
                ],
            )
            profile = DebuggerProfileBuilder(env).build()

            VscodeConfigurator(env).update_vscode_debugger_launcher()

            launch_json = os.path.join(project_dir, ".vscode", "launch.json")
            with open(launch_json, encoding="utf-8") as launch_file:
                payload = json.load(launch_file)
            odoo_unit = next(
                unit
                for unit in payload["configurations"]
                if unit["name"] == constants.DEBUGGER_UNIT_NAME
            )
            self.assertEqual(odoo_unit["port"], profile.debugger.port)
            self.assertEqual(odoo_unit["host"], profile.debugger.host)
            local_roots = [
                mapping["localRoot"] for mapping in odoo_unit["pathMappings"]
            ]
            self.assertEqual(local_roots, [os.path.realpath(odoo_src)])

    def test_update_vscode_debugger_launcher_writes_symlink_local_roots(self) -> None:
        with tempfile.TemporaryDirectory() as project_dir:
            real_developing = os.path.join(project_dir, "sources", "app")
            os.makedirs(real_developing)
            link_path = os.path.join(project_dir, "app")
            os.symlink(real_developing, link_path)

            env = make_debugger_env_mock(
                project_dir=project_dir,
                symlinks_sources=[
                    SymlinksSources(source_path=real_developing, link_path=link_path)
                ],
                mapped_folders=[
                    MappedPath(
                        local=real_developing,
                        docker="/home/odoo/extra-addons/app",
                    ),
                ],
            )

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
            self.assertIn(os.path.realpath(real_developing), local_roots)
            self.assertIn(os.path.abspath(link_path), local_roots)


if __name__ == "__main__":
    unittest.main()
