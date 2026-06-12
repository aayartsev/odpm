"""Integration tests for nested odpm.json discovery: lock, requirements, CI strict."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
import unittest
from dev_project.host.cli.args import OdpmCliArgs
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.config import Config, config_to_json
from dev_project.config.state import DockerLayoutState, ProjectSettingsState, UserSettingsState
from dev_project.dependency_resolver import DependencyResolutionResult, NestedOdpmFragment
from dev_project.errors import PipelineError
from dev_project.git.deps_lock import canonical_repo_url, load_deps_lock
from dev_project.git.deps_lock_manager import DepsLockManager
from dev_project.project_env.links import ProjectLinks
from dev_project.scenario_policy import ScenarioPolicy

from tests.test_deps_lock_integration import _config_stub, _git_link_at, _init_git_repo


def _commit_file(repo_path: str, filename: str, content: str) -> None:
    Path(repo_path, filename).write_text(content, encoding="utf-8")
    subprocess.run(["git", "add", filename], cwd=repo_path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", f"add {filename}"],
        cwd=repo_path,
        check=True,
        capture_output=True,
    )


def _cloned_link(repo_path: str, url: str):
    link = _git_link_at(repo_path, url)
    link.is_cloned = True
    return link


def _map_folders_config_stub(*, scenario: str = constants.DEVELOPER_SCENARIO) -> Config:
    config = Config.__new__(Config)
    config._project = ProjectSettingsState(
        odoo_version="17.0",
        python_version="3.12",
        requirements_txt=["requests==2.31.0"],
        dependencies=[],
    )
    config._user = UserSettingsState(use_oca_dependencies=True)
    config.policy = ScenarioPolicy.from_scenario(scenario)
    config.user_env = MagicMock()
    config.user_env.debugger_backend = "debugpy_listen"
    config.arguments = OdpmCliArgs(no_git_update=False)
    config.skip_git_update = Config.skip_git_update.__get__(config, Config)
    config.apply_transitive_requirements = Config.apply_transitive_requirements.__get__(
        config, Config
    )
    config._docker = DockerLayoutState(
        venv_dir="/tmp/venv",
        odoo_tests_dir="/tmp/tests",
        docker_odoo_dir="/docker/odoo",
        docker_venv_dir="/docker/venv",
        docker_temp_tests_dir="/docker/tests",
        docker_dev_project_dir="/docker/dev_project",
        docker_backups_dir="/docker/backups",
        docker_project_dir="/docker/project",
        dir_for_odoo_container_home="/tmp/home",
        docker_odoo_project_dir_path="/docker/project",
        docker_extra_addons="/docker/addons",
        dependencies_projects=[],
        dependencies_dirs=[],
        docker_dirs_with_addons=[],
        docker_path_odoo_conf="/home/odoo/odoo.conf",
        odoo_config_data={},
    )
    config.program_dir = "/tmp/program"
    config.odoo_src_dir = "/tmp/odoo"
    config.developing_project_dir_path = "/tmp/developing"
    config.developing_project = MagicMock(project_path="")
    config.pre_commit_map_files = []
    config.check_project_for_subprojects = MagicMock(return_value=[])
    config.catalogs_of_modules_data = []
    config.platform_name = "odoo"
    config.arch = "amd64"
    config.sql_queries = []
    config.update_modules = ""
    config.container_run_mode = constants.RUN_MODE_ODOO
    config.db_creation_data = constants.DEFAULT_DB_CREATION_DATA
    config.db_manager_password = ""
    config.user_env = MagicMock(odpm_scenario=scenario)
    return config


class NestedOdpmIntegrationTests(unittest.TestCase):
    def test_resolve_discovers_nested_dependency_from_real_odpm_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            framework_url = "https://github.com/test/framework.git"
            nested_url = "https://github.com/test/nested.git"
            framework_path = os.path.join(tmp, "framework")
            nested_path = os.path.join(tmp, "nested")
            _init_git_repo(framework_path)
            _init_git_repo(nested_path)
            _commit_file(
                framework_path,
                "odpm.json",
                json.dumps(
                    {
                        "dependencies": [nested_url],
                        "requirements_txt": ["openupgradelib"],
                    }
                ),
            )

            def handle_git_link(url, materialize=False, system_type="standart"):
                if url == framework_url:
                    return _cloned_link(framework_path, framework_url)
                if url == nested_url:
                    return _cloned_link(nested_path, nested_url)
                return _cloned_link("", url)

            config = _map_folders_config_stub()
            config.dependencies = [framework_url]
            config.handle_git_link = MagicMock(side_effect=handle_git_link)
            env = MagicMock(config=config)
            links = ProjectLinks(env)
            links.checkout_project = MagicMock()

            result = links._resolve_dependencies()

            self.assertEqual(result.urls, [framework_url, nested_url])
            self.assertEqual(result.transitive_requirements, ["openupgradelib"])
            self.assertEqual(len(result.nested_fragments), 1)

    def test_collect_lock_includes_nested_transitive_dependency(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = os.path.join(tmp, "project")
            os.makedirs(os.path.join(project_dir, ".odpm"), exist_ok=True)
            platform_dir = os.path.join(tmp, "platform")
            framework_path = os.path.join(tmp, "framework")
            nested_path = os.path.join(tmp, "nested")
            platform_url = "https://github.com/test/platform.git"
            framework_url = "https://github.com/test/framework.git"
            nested_url = "https://github.com/test/nested.git"
            _init_git_repo(platform_dir)
            _init_git_repo(framework_path)
            _init_git_repo(nested_path)
            _commit_file(
                framework_path,
                "odpm.json",
                json.dumps({"dependencies": [nested_url]}),
            )

            platform = _cloned_link(platform_dir, platform_url)
            framework = _cloned_link(framework_path, framework_url)
            nested = _cloned_link(nested_path, nested_url)
            config = _config_stub(
                project_dir,
                constants.DEVELOPER_SCENARIO,
                platform=platform,
                dependencies_projects=[framework, nested],
            )
            config.seed_dependency_urls = MagicMock(return_value=[framework_url])

            DepsLockManager(config).collect_and_save()

            lock = load_deps_lock(os.path.join(project_dir, ".odpm", "deps.lock.json"))
            self.assertIsNotNone(lock)
            assert lock is not None
            locked_urls = {entry.url for entry in lock.dependencies}
            self.assertIn(canonical_repo_url(framework_url), locked_urls)
            self.assertIn(canonical_repo_url(nested_url), locked_urls)

    def test_map_folders_merges_requirements_into_runtime_config(self):
        config = _map_folders_config_stub()
        url = "https://github.com/acme/A.git"
        dependency = MagicMock(
            is_cloned=True,
            project_path="/tmp/dep",
            inside_docker_path="dep",
        )
        dependency.project_data.project_type = constants.TYPE_PROJECT_PROJECT
        config.handle_git_link = MagicMock(return_value=dependency)
        env = MagicMock(config=config)
        env.mapped_folders = []
        links = ProjectLinks(env)
        links._resolve_dependencies = MagicMock(
            return_value=DependencyResolutionResult(
                urls=[url],
                transitive_requirements=["openupgradelib"],
                nested_fragments=[],
            )
        )

        with patch(
            "dev_project.config.payload.compute_venv_lock_hash",
            return_value="lock-hash",
        ):
            links.map_folders()
            payload = json.loads(config_to_json(config).decode("utf-8"))

        self.assertIn("openupgradelib", payload["requirements_txt"])
        self.assertIn("requests==2.31.0", payload["requirements_txt"])

    def test_map_folders_ci_nested_version_mismatch_raises_pipeline_error(self):
        config = _map_folders_config_stub(scenario=constants.CI_SCENARIO)
        url = "https://github.com/acme/A.git"
        dependency = MagicMock(
            is_cloned=True,
            project_path="/tmp/dep",
            inside_docker_path="dep",
        )
        dependency.project_data.project_type = constants.TYPE_PROJECT_PROJECT
        config.handle_git_link = MagicMock(return_value=dependency)
        env = MagicMock(config=config)
        env.mapped_folders = []
        links = ProjectLinks(env)
        links._resolve_dependencies = MagicMock(
            return_value=DependencyResolutionResult(
                urls=[url],
                transitive_requirements=[],
                nested_fragments=[
                    NestedOdpmFragment(
                        dependencies=[],
                        requirements_txt=[],
                        odoo_version="19.0",
                        python_version=None,
                        source_path="/tmp/framework/odpm.json",
                    )
                ],
            )
        )

        with self.assertRaises(PipelineError):
            links.map_folders()


if __name__ == "__main__":
    unittest.main()
