"""Unit tests for autoreload probe helpers."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from tests.integration.dev_mode_reload_probe import (
    AUTO_RELOAD_TRIGGERED_RE,
    classify_autoreload_support,
    repo_basename_from_developing_link,
    resolve_developing_project_local_path,
    resolve_probe_python_file,
)


class DevModeReloadProbeTests(unittest.TestCase):
    SAMPLE_COMPOSE = """
services:
  odoo:
    volumes:
      - /data/demo-project:/home/odoo/extra-addons/demo-project:Z
"""

    def test_repo_basename_from_developing_link(self):
        self.assertEqual(
            repo_basename_from_developing_link(
                "git@github.com:example/demo-project.git"
            ),
            "demo-project",
        )

    def test_classify_autoreload_support(self):
        self.assertEqual(
            classify_autoreload_support(
                "WARNING ... 'inotify' module not installed. Code autoreload feature is disabled"
            ),
            "disabled",
        )
        self.assertEqual(
            classify_autoreload_support("INFO AutoReload watcher running with inotify"),
            "watcher_active",
        )

    def test_resolve_developing_project_local_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            local_repo = root / "repos" / "demo-project"
            local_repo.mkdir(parents=True)
            (root / "user_settings.json").write_text(
                json.dumps(
                    {
                        "developing_project": "git@github.com:example/demo-project.git"
                    }
                ),
                encoding="utf-8",
            )
            (root / "docker-compose.yml").write_text(
                self.SAMPLE_COMPOSE.replace("/data/demo-project", str(local_repo)),
                encoding="utf-8",
            )
            resolved = resolve_developing_project_local_path(root)
            self.assertEqual(resolved, local_repo)

    def test_resolve_probe_python_file_prefers_init_module(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            local_repo = root / "repos" / "demo-project"
            module_dir = local_repo / "demo_module"
            module_dir.mkdir(parents=True)
            probe = module_dir / "__init__.py"
            probe.write_text("# module\n", encoding="utf-8")
            (root / "user_settings.json").write_text(
                json.dumps(
                    {
                        "developing_project": "git@github.com:example/demo-project.git",
                        "init_modules": "demo_module,other",
                    }
                ),
                encoding="utf-8",
            )
            (root / "docker-compose.yml").write_text(
                self.SAMPLE_COMPOSE.replace("/data/demo-project", str(local_repo)),
                encoding="utf-8",
            )
            self.assertEqual(resolve_probe_python_file(root), probe)

    def test_autoreload_trigger_regex(self):
        self.assertTrue(
            AUTO_RELOAD_TRIGGERED_RE.search(
                "INFO autoreload: python code updated, autoreload activated"
            )
        )

    @patch("tests.integration.dev_mode_reload_probe.fetch_odoo_logs")
    @patch("tests.integration.dev_mode_reload_probe.wait_for_autoreload_trigger")
    @patch("tests.integration.dev_mode_reload_probe.append_probe_comment")
    @patch("tests.integration.dev_mode_reload_probe.restore_probe_file")
    def test_run_autoreload_probe_success(
        self,
        _restore,
        mock_append,
        mock_wait,
        mock_logs,
    ):
        from tests.integration.dev_mode_reload_probe import run_autoreload_probe

        mock_logs.return_value = "INFO AutoReload watcher running with inotify"
        mock_append.return_value = "# original\n"
        mock_wait.return_value = True
        mock_logs.side_effect = [
            "INFO AutoReload watcher running with inotify",
            "INFO autoreload: python code updated, autoreload activated",
        ]

        with tempfile.NamedTemporaryFile(suffix=".py") as probe:
            result = run_autoreload_probe([], Path("/tmp"), Path(probe.name))
        self.assertEqual(result.outcome, "activated")
