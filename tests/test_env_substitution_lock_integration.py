"""Integration: manifest env expansion → seed URLs → deps.lock collect."""

from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.config import Config
from dev_project.config.manifests import OdpmJsonReader
from dev_project.config.state import BootstrapState, DockerLayoutState
from dev_project.config.transforms.env_substitution import EnvResolver
from dev_project.git import HandleOdooProjectLink
from dev_project.git.deps_lock import canonical_repo_url, load_deps_lock
from dev_project.git.deps_lock_manager import DepsLockManager
from dev_project.scenario_policy import ScenarioPolicy

from tests.test_deps_lock_integration import _git_link_at


def _file_link_at(repo_path: str) -> HandleOdooProjectLink:
    return _git_link_at(
        repo_path,
        f"file://{repo_path}",
        link_type=constants.GITLINK_TYPE_FILE,
    )


class EnvSubstitutionDepsLockIntegrationTests(unittest.TestCase):
    def test_collect_and_save_writes_resolved_file_urls_from_expanded_odpm_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            platform_dir = os.path.join(tmp, "platform")
            dep_dir = os.path.join(tmp, "oca_web")
            dev_repo = os.path.join(tmp, "dev_repo")
            project_dir = os.path.join(tmp, "project")
            for path in (platform_dir, dep_dir, dev_repo):
                os.makedirs(path)
            os.makedirs(os.path.join(project_dir, constants.PROJECT_SERVICE_DIRECTORY))

            Path(platform_dir, "odoo-bin").write_text("bin", encoding="utf-8")
            odpm_path = os.path.join(dev_repo, constants.PROJECT_CONFIG_FILE_NAME)
            Path(odpm_path).write_text(
                json.dumps(
                    {
                        "odpm_version": constants.ODPM_VERSION,
                        "odoo_git_link": "file://${ODOO_PLATFORM_DIR}",
                        "dependencies": ["file://${OCA_WEB_PATH}"],
                    }
                ),
                encoding="utf-8",
            )

            resolver = EnvResolver.from_sources(
                process_environ={},
                project_dotenv={
                    "ODOO_PLATFORM_DIR": platform_dir,
                    "OCA_WEB_PATH": dep_dir,
                },
            )
            config = MagicMock()
            config._raw_odpm_json = {}
            config.repo_odpm_json = odpm_path
            config.project_odpm_json = os.path.join(
                project_dir, constants.PROJECT_CONFIG_FILE_NAME
            )
            config.env_resolver = resolver

            OdpmJsonReader(config, rewrite_odpm_json=MagicMock()).get_odpm_settings()

            resolved_platform_url = f"file://{platform_dir}"
            resolved_dep_url = f"file://{dep_dir}"
            self.assertEqual(config._raw_odpm_json["odoo_git_link"], resolved_platform_url)
            self.assertEqual(config._raw_odpm_json["dependencies"], [resolved_dep_url])

            lock_config = Config.__new__(Config)
            lock_config._bootstrap = BootstrapState()
            lock_config._docker = DockerLayoutState()
            lock_config._raw_odpm_json = dict(config._raw_odpm_json)
            lock_config.project_dir = project_dir
            lock_config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
            lock_config.odoo_platform_project = _file_link_at(platform_dir)
            lock_config.dependencies_projects = [_file_link_at(dep_dir)]
            lock_config.developing_project = _file_link_at(dev_repo)

            self.assertEqual(
                Config.seed_dependency_urls(lock_config),
                [resolved_dep_url],
            )

            DepsLockManager(lock_config).collect_and_save(
                developing=lock_config.developing_project,
            )

            lock_path = os.path.join(
                project_dir,
                constants.PROJECT_SERVICE_DIRECTORY,
                "deps.lock.json",
            )
            lock = load_deps_lock(lock_path)
            self.assertIsNotNone(lock)
            assert lock is not None

            lock_text = Path(lock_path).read_text(encoding="utf-8")
            self.assertNotIn("${", lock_text)

            self.assertEqual(lock.platform.kind, "file")
            self.assertEqual(
                canonical_repo_url(lock.platform.url),
                canonical_repo_url(resolved_platform_url),
            )
            self.assertEqual(len(lock.dependencies), 1)
            self.assertEqual(lock.dependencies[0].kind, "file")
            self.assertEqual(
                canonical_repo_url(lock.dependencies[0].url),
                canonical_repo_url(resolved_dep_url),
            )

    def test_seed_coverage_passes_when_lock_matches_expanded_manifest_seeds(self):
        with tempfile.TemporaryDirectory() as project_dir:
            dep_dir = os.path.join(project_dir, "dep")
            platform_dir = os.path.join(project_dir, "platform")
            dev_dir = os.path.join(project_dir, "dev")
            for path in (dep_dir, platform_dir, dev_dir):
                os.makedirs(path)
            os.makedirs(os.path.join(project_dir, constants.PROJECT_SERVICE_DIRECTORY))

            resolved_dep_url = f"file://{dep_dir}"
            expanded_manifest = {
                "dependencies": [resolved_dep_url],
                "odoo_git_link": f"file://{platform_dir}",
            }

            config = Config.__new__(Config)
            config._bootstrap = BootstrapState()
            config._docker = DockerLayoutState()
            config._raw_odpm_json = expanded_manifest
            config.project_dir = project_dir
            config.policy = ScenarioPolicy.from_scenario(constants.CI_SCENARIO)
            config.odoo_platform_project = _file_link_at(platform_dir)
            config.dependencies_projects = [_file_link_at(dep_dir)]
            config.developing_project = _file_link_at(dev_dir)

            DepsLockManager(config).collect_and_save(developing=config.developing_project)

            manager = DepsLockManager(config)
            manager.load()
            manager.enter_apply_mode()

            manager._check_seed_coverage()


if __name__ == "__main__":
    unittest.main()
