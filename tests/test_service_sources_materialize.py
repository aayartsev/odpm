"""Tests for service_sources materialize and prepare step."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest import mock

from dev_project.config.transforms.env_substitution import EnvResolver
from dev_project.errors import ConfigError
from dev_project.git import service_sources as service_sources_mod
from dev_project.git.service_sources import (
    SERVICE_SOURCES_DIR,
    apply_materialized_service_sources,
    collect_service_source_paths,
    materialize_one_service_source,
    service_source_target_dir,
    service_sources_need_materialize,
)
from dev_project.manifest.reader import load_manifest
from dev_project.prepare.registry import BUILTIN_PREPARE_STEPS
from dev_project.prepare.steps_sources import (
    evaluate_sources_materialize,
    exec_sources_materialize,
)
from tests.test_manifest_v2_reader import _minimal_v2
from dev_project.config.config import Config
from dev_project import constants
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.host.context import HostProjectContext
from dev_project.host.ports import ports_from_config
from dev_project.prepare.types import PrepareContext
from dev_project.scenario_policy import ScenarioPolicy


class ServiceSourcesMaterializeTests(unittest.TestCase):
    def test_file_source_returns_absolute_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = mock.MagicMock()
            config.user_env.odoo_projects_dir = tmp
            path = materialize_one_service_source(
                config,
                "fixtures",
                f"file://{tmp}",
            )
            self.assertEqual(path, os.path.abspath(tmp))

    def test_file_source_missing_raises(self):
        config = mock.MagicMock()
        with self.assertRaises(ConfigError):
            materialize_one_service_source(
                config,
                "fixtures",
                "file:///nonexistent/service-source",
            )

    def test_git_source_clones_into_service_sources_name_dir(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = mock.MagicMock()
            config.user_env.odoo_projects_dir = tmp
            config.skip_git_update.return_value = False
            config.odoo_version = "17.0"
            config.user_settings.clean_git_repos = False
            config.user_settings.update_git_repos = False

            project_link = mock.MagicMock()
            project_link.gitlink = "https://github.com/org/autoparts-env.git"
            project_link.branch = "17.0"
            project_link.branch_explicit = True
            project_link.commit_explicit = False
            config.handle_git_link.return_value = project_link

            expected = service_source_target_dir(config, "autoparts_env")

            with mock.patch.object(
                service_sources_mod,
                "_clone_service_source_repo",
            ) as clone_mock:
                clone_mock.side_effect = lambda link, **kwargs: setattr(
                    link, "project_path", kwargs["target_dir"]
                )

                def isdir_side_effect(path):
                    if str(path).endswith(".git"):
                        return False
                    return os.path.abspath(str(path)) == expected

                with mock.patch("os.path.isdir", side_effect=isdir_side_effect):
                    path = materialize_one_service_source(
                        config,
                        "autoparts_env",
                        "https://github.com/org/autoparts-env.git 17.0",
                    )

            self.assertEqual(path, expected)
            clone_mock.assert_called_once()
            project_link.checkout_repository.assert_called_once()

    def test_need_materialize_false_when_git_dir_exists(self):
        with tempfile.TemporaryDirectory() as tmp:
            source_root = os.path.join(tmp, SERVICE_SOURCES_DIR, "autoparts_env")
            os.makedirs(os.path.join(source_root, ".git"))

            view = load_manifest(
                _minimal_v2(
                    service_sources={
                        "autoparts_env": "https://github.com/org/autoparts-env.git 17.0",
                    },
                ),
            )
            config = mock.MagicMock()
            config.bootstrap.manifest_view = view
            config.user_env.odoo_projects_dir = tmp

            self.assertFalse(service_sources_need_materialize(config))

    def test_apply_injects_resolver_and_reexpands_services(self):

        view = load_manifest(
            _minimal_v2(
                service_sources={
                    "autoparts_env": "https://github.com/org/autoparts-env.git 17.0",
                },
                services={
                    "armtek_test": {
                        "image": "autoparts_env:emulator",
                        "volumes": ["${@source:autoparts_env}/data:/data:Z"],
                    }
                },
            ),
            env_resolver=EnvResolver.from_sources(process_environ={}, project_dotenv={}),
        )
        config = mock.MagicMock(spec=Config)
        config.bootstrap.manifest_view = view
        config._env_resolver = EnvResolver.from_sources(
            process_environ={},
            project_dotenv={},
        )
        type(config).env_resolver = property(lambda self: self._env_resolver)

        with mock.patch(
            "dev_project.git.service_sources.SymlinkManager"
        ) as manager_cls:
            apply_materialized_service_sources(
                config,
                {"autoparts_env": "/opt/autoparts-env"},
            )
            manager_cls.return_value.sync_service_source_project_links.assert_called_once_with(
                {"autoparts_env": "/opt/autoparts-env"},
            )

        self.assertEqual(
            config.bootstrap.service_source_paths,
            {"autoparts_env": "/opt/autoparts-env"},
        )
        self.assertEqual(
            config.bootstrap.manifest_view.services["armtek_test"]["volumes"],
            ["/opt/autoparts-env/data:/data:Z"],
        )

    def test_collect_paths_for_file_and_git_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            local = os.path.join(tmp, "local-env")
            os.makedirs(local)
            view = load_manifest(
                _minimal_v2(
                    service_sources={
                        "autoparts_env": "https://github.com/org/autoparts-env.git 17.0",
                        "local_env": f"file://{local}",
                    },
                ),
            )
            config = mock.MagicMock()
            config.bootstrap.manifest_view = view
            config.user_env.odoo_projects_dir = tmp

            paths = collect_service_source_paths(config)
            self.assertEqual(paths["local_env"], os.path.abspath(local))
            self.assertEqual(
                paths["autoparts_env"],
                service_source_target_dir(config, "autoparts_env"),
            )


class ServiceSourcesPrepareStepTests(unittest.TestCase):
    def test_prepare_registry_includes_sources_materialize_after_git_materialize(self):
        ids = [step.id for step in BUILTIN_PREPARE_STEPS]
        git_index = ids.index("git.materialize")
        sources_index = ids.index("sources.materialize")
        hooks_index = ids.index("hooks.post_clone")
        self.assertEqual(sources_index, git_index + 1)
        self.assertEqual(hooks_index, sources_index + 1)

    def _make_ctx(self, project_dir: str, *, service_sources: dict | None) -> PrepareContext:
        config = mock.MagicMock()
        config.project_dir = project_dir
        config.service_sources_dir = os.path.join(project_dir, constants.SERVICE_SOURCES_DIR)
        config.symlinks_sources = []
        config.repo_odpm_json = os.path.join(project_dir, "odpm.json")
        config.bootstrap = mock.MagicMock()
        if service_sources is None:
            config.bootstrap.manifest_view = None
        else:
            config.bootstrap.manifest_view = load_manifest(
                _minimal_v2(service_sources=service_sources),
            )
        config.user_env = mock.MagicMock()
        config.user_env.odoo_projects_dir = os.path.join(project_dir, "odoo_projects")
        config.policy = ScenarioPolicy.from_scenario(constants.DEVELOPER_SCENARIO)
        host_ctx = HostProjectContext.from_config(config)
        ports = ports_from_config(config, mock.MagicMock(), OdpmCliArgs())
        return PrepareContext(
            ports=ports,
            project_env=mock.MagicMock(),
            templates=mock.MagicMock(),
            compose_generator=mock.MagicMock(),
            links=mock.MagicMock(),
            system_checker=mock.MagicMock(),
            args=mock.MagicMock(),
            host_ctx=host_ctx,
        )

    def test_evaluate_empty_sources_is_run_not_noop(self):
        with tempfile.TemporaryDirectory() as project_dir:
            ctx = self._make_ctx(project_dir, service_sources=None)
            step = evaluate_sources_materialize(ctx)
            self.assertEqual(step.outcome, "run")
            self.assertTrue(step.should_execute())

    def test_exec_empty_sources_removes_stale_project_links(self):
        with tempfile.TemporaryDirectory() as project_dir:
            link_dir = os.path.join(project_dir, constants.SERVICE_SOURCES_DIR)
            os.makedirs(link_dir)
            stale_target = os.path.join(project_dir, "old-clone")
            os.makedirs(stale_target)
            stale_link = os.path.join(link_dir, "autoparts_env")
            os.symlink(stale_target, stale_link)

            ctx = self._make_ctx(project_dir, service_sources={})
            exec_sources_materialize(ctx)

            self.assertFalse(os.path.lexists(stale_link))
            self.assertTrue(os.path.isdir(link_dir))


if __name__ == "__main__":
    unittest.main()
