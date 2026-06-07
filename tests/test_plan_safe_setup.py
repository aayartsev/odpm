"""Plan mode must not mutate ``.odpm/`` templates during setup."""

from __future__ import annotations

import tempfile
import unittest
from dev_project.host.cli.args import OdpmCliArgs
from tests.cli_test_helpers import cli_args
from pathlib import Path
from unittest.mock import MagicMock, patch

from dev_project import constants
from dev_project.config.bootstrap import load_project_settings
from dev_project.odpm_pipeline import OdpmPipeline
from dev_project.project_dir_manager import ProjectDirManager
from tests.plan_smoke_helpers import repo_root, seed_migrated_project_layout


def _program_dir() -> str:
    return str(repo_root())


def _odpm_snapshot(project_dir: Path) -> dict[str, tuple[int, bytes]]:
    odpm_dir = project_dir / constants.PROJECT_SERVICE_DIRECTORY
    snapshot: dict[str, tuple[int, bytes]] = {}
    if not odpm_dir.is_dir():
        return snapshot
    for path in sorted(odpm_dir.rglob("*")):
        if path.is_file():
            rel = str(path.relative_to(project_dir))
            snapshot[rel] = (path.stat().st_mtime_ns, path.read_bytes())
    return snapshot


class PlanSafeProjectDirManagerTests(unittest.TestCase):
    def _args(self) -> OdpmCliArgs:
        return cli_args(odoo_git_link=None)

    def test_sync_templates_false_preserves_odpm_tree(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            seed_migrated_project_layout(project_dir)
            dockerignore = (
                project_dir
                / constants.PROJECT_DOCKERIGNORE_TEMPLATE_FILE_RELATIVE_PATH
            )
            dockerignore.write_text("**/.git\n.venv\n", encoding="utf-8")
            before = _odpm_snapshot(project_dir)

            ProjectDirManager(
                str(project_dir),
                self._args(),
                _program_dir(),
                sync_templates=False,
            )

            self.assertEqual(_odpm_snapshot(project_dir), before)

    def test_sync_templates_true_upgrades_legacy_dockerignore(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_dir = Path(tmp)
            seed_migrated_project_layout(project_dir)
            dockerignore = (
                project_dir
                / constants.PROJECT_DOCKERIGNORE_TEMPLATE_FILE_RELATIVE_PATH
            )
            dockerignore.write_text("**/.git\n.venv\n", encoding="utf-8")

            ProjectDirManager(str(project_dir), self._args(), _program_dir())

            content = dockerignore.read_text(encoding="utf-8")
            self.assertIn(".odpm/ci-build-context", content)


class PlanSafeBootstrapTests(unittest.TestCase):
    def _config(self, *, sync_templates: bool):
        from dev_project.config import Config
        from dev_project.config.state import ProjectSettingsState

        config = Config.__new__(Config)
        config._raw_odpm_json = {
            "odoo_version": "18.0",
            "python_version": "3.12",
            "odpm_version": constants.ODPM_VERSION,
        }
        config.arguments = OdpmCliArgs(
            odoo_version=None,
            python_version=None,
            distro_name=None,
            distro_version=None,
            postgres_version=None,
            requirements_txt="",
        )
        from dev_project.config.transforms import OdooBuildDateResolver

        config._project = ProjectSettingsState()
        config._loader = MagicMock()
        config._build_date = OdooBuildDateResolver(config)
        config._raw_odpm_json["odoo_build_date"] = constants.ODOO_DEFAULT_BUILD_DATE
        config.repo_odpm_json = "/tmp/project/odpm.json"
        config.pd_manager = MagicMock(
            sync_templates=sync_templates,
            project_docker_compose_template_path="/tmp/project/.odpm/docker-compose.yml",
        )
        return config

    @patch("dev_project.config.bootstrap.os.path.exists")
    def test_load_project_settings_skips_compose_rebuild_when_not_syncing(
        self, mock_exists
    ):
        config = self._config(sync_templates=False)
        mock_exists.side_effect = lambda path: path == config.repo_odpm_json

        load_project_settings(config)

        config.pd_manager.rebuild_docker_compose_template.assert_not_called()

    @patch("dev_project.config.bootstrap.os.path.exists")
    def test_load_project_settings_rebuilds_missing_compose_when_syncing(
        self, mock_exists
    ):
        config = self._config(sync_templates=True)
        mock_exists.side_effect = lambda path: path == config.repo_odpm_json

        load_project_settings(config)

        config.pd_manager.rebuild_docker_compose_template.assert_called_once()


class PlanSafePipelineSetupTests(unittest.TestCase):
    @patch("dev_project.odpm_pipeline.SystemChecker")
    @patch("dev_project.odpm_pipeline.CreateProjectEnvironment")
    @patch("dev_project.odpm_pipeline.Config")
    @patch("dev_project.odpm_pipeline.CreateUserEnvironment")
    @patch("dev_project.odpm_pipeline.ProjectDirManager")
    def test_setup_for_plan_disables_template_sync(
        self,
        mock_pd_manager_cls,
        _mock_user_env_cls,
        _mock_config_cls,
        _mock_project_env_cls,
        _mock_checker_cls,
    ):
        pipeline_args = OdpmCliArgs(plan=True)
        pipeline = OdpmPipeline(
            pipeline_args,
            "/opt/odpm",
            start_dir="/tmp/project",
        )

        pipeline.setup(for_plan=True)

        mock_pd_manager_cls.assert_called_once_with(
            "/tmp/project",
            pipeline_args,
            "/opt/odpm",
            sync_templates=False,
        )
        self.assertIs(pipeline.cli_args, mock_pd_manager_cls.return_value.arguments)

    @patch("dev_project.odpm_pipeline.SystemChecker")
    @patch("dev_project.odpm_pipeline.CreateProjectEnvironment")
    @patch("dev_project.odpm_pipeline.Config")
    @patch("dev_project.odpm_pipeline.CreateUserEnvironment")
    @patch("dev_project.odpm_pipeline.ProjectDirManager")
    def test_setup_default_enables_template_sync(
        self,
        mock_pd_manager_cls,
        _mock_user_env_cls,
        _mock_config_cls,
        _mock_project_env_cls,
        _mock_checker_cls,
    ):
        pipeline_args = OdpmCliArgs(build_image=False)
        pipeline = OdpmPipeline(
            pipeline_args,
            "/opt/odpm",
            start_dir="/tmp/project",
        )

        pipeline.setup()

        mock_pd_manager_cls.assert_called_once_with(
            "/tmp/project",
            pipeline_args,
            "/opt/odpm",
            sync_templates=True,
        )
        self.assertIs(pipeline.cli_args, mock_pd_manager_cls.return_value.arguments)


if __name__ == "__main__":
    unittest.main()
