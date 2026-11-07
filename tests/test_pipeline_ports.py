"""Pipeline host ports contract tests."""

from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

from dev_project.config.assembly import ports_from_assembled
from dev_project.config.state import BOOTSTRAP_HANDLE_SURFACES, CONFIG_PROPERTY_SHIMS
from dev_project.git.deps_lock_manager import DepsLockManager
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.host.context import HostProjectContext
from dev_project.host.ports import (
    BootstrapHandle,
    ComposePorts,
    PipelinePorts,
    PlanPorts,
    RuntimePorts,
)
from dev_project.manifest.reader import ManifestView
from dev_project.project_env import CreateProjectEnvironment


class PipelinePortsTests(unittest.TestCase):
    def test_ports_from_assembled_builds_shared_bootstrap_and_host_ctx(self):
        config = MagicMock()
        config.arguments = OdpmCliArgs()
        config.user_env = MagicMock()
        project_env = CreateProjectEnvironment(BootstrapHandle(_assembled=config))

        ports = ports_from_assembled(config, project_env, OdpmCliArgs())

        self.assertIsInstance(ports.plan, PlanPorts)
        self.assertIsInstance(ports.compose, ComposePorts)
        self.assertIsInstance(ports.runtime, RuntimePorts)
        self.assertIs(ports.plan.bootstrap, ports.compose.bootstrap)
        self.assertIs(ports.plan.bootstrap, ports.runtime.bootstrap)
        self.assertIs(ports.bootstrap._assembled, config)
        self.assertIs(ports.compose.project_env, project_env)
        self.assertIs(ports.runtime.project_env, project_env)
        self.assertIsInstance(ports.plan.host_ctx, HostProjectContext)

    def test_ports_from_assembled_without_project_env(self):
        config = MagicMock()
        config.arguments = OdpmCliArgs()
        config.user_env = MagicMock()

        ports = ports_from_assembled(config)

        self.assertIsInstance(ports, PipelinePorts)
        self.assertIsInstance(ports.compose.project_env, CreateProjectEnvironment)

    def test_bootstrap_handle_exposes_manifest_read_model(self):

        config = MagicMock()
        view = ManifestView(
            manifest_schema=2,
            requires_odpm=">=4.5.0",
            services=None,
            hooks=None,
            locks=None,
            raw_normalized={},
            source_raw={},
        )
        config.bootstrap.manifest_view = view
        config.bootstrap.repo_odpm_json = "/tmp/project/odpm.json"

        bootstrap = BootstrapHandle(_assembled=config)

        self.assertIs(bootstrap.manifest_view, view)
        self.assertEqual(bootstrap.repo_odpm_json, "/tmp/project/odpm.json")

    def test_bootstrap_handle_exposes_narrow_git_and_lock_surfaces(self):
        config = MagicMock()
        config._git_repos = MagicMock(name="git_repos")
        config.compute_venv_lock_hash.return_value = "abc123"

        bootstrap = BootstrapHandle(_assembled=config)

        self.assertIs(bootstrap.git_repos, config._git_repos)
        self.assertEqual(bootstrap.compute_venv_lock_hash(), "abc123")
        lock_manager = bootstrap.new_lock_manager()

        self.assertIsInstance(lock_manager, DepsLockManager)

    def test_bootstrap_handle_exposes_env_odoo_conf_pd_manager(self):
        config = MagicMock()
        config.env_resolver = MagicMock(name="env_resolver")
        config._odoo_conf = MagicMock(name="odoo_conf")
        config.pd_manager = MagicMock(name="pd_manager")

        bootstrap = BootstrapHandle(_assembled=config)

        self.assertIs(bootstrap.env_resolver, config.env_resolver)
        self.assertIs(bootstrap.odoo_conf, config._odoo_conf)
        self.assertIs(bootstrap.pd_manager, config.pd_manager)

    def test_bootstrap_handle_git_symlink_nested_workspace_accessors(self):
        config = MagicMock()
        link = MagicMock(name="git_link")
        config._git_repos.handle_git_link.return_value = link
        config.developing_project = MagicMock(name="developing")
        config.odoo_platform_project = MagicMock(name="platform")
        config.odoo_src_dir = "/tmp/odoo"
        config.developing_project_dir_path = "/tmp/dev"

        bootstrap = BootstrapHandle(_assembled=config)

        self.assertIs(
            bootstrap.handle_git_link("git@x/y", materialize=True),
            link,
        )
        config._git_repos.handle_git_link.assert_called_once_with(
            "git@x/y",
            materialize=True,
        )
        config._git_repos.handle_git_link.reset_mock()
        bootstrap.handle_git_link("git@x/y", system_type="platform", materialize=False)
        config._git_repos.handle_git_link.assert_called_once_with(
            "git@x/y",
            system_type="platform",
            materialize=False,
        )

        with patch(
            "dev_project.symlinks.ensure_git_repo_symlink"
        ) as mock_symlink:
            bootstrap.ensure_git_repo_symlink("/tmp/repo", scope="dependency")
            mock_symlink.assert_called_once_with(
                bootstrap, "/tmp/repo", scope="dependency"
            )

        with patch(
            "dev_project.symlinks.ensure_developing_repo_symlinks"
        ) as mock_dev_symlinks:
            bootstrap.ensure_developing_repo_symlinks()
            mock_dev_symlinks.assert_called_once_with(bootstrap)

        fragments = [MagicMock(name="fragment")]
        with patch(
            "dev_project.config.nested_compatibility.collect_nested_compatibility_issues",
            return_value=[],
        ) as mock_issues:
            bootstrap.apply_nested_compatibility(fragments)
            mock_issues.assert_called_once()

        bootstrap.generate_odoo_conf_docker_data()
        config._odoo_conf.generate_odoo_conf_docker_data.assert_called_once_with()

        self.assertIs(bootstrap.developing_project, config.developing_project)
        self.assertIs(bootstrap.odoo_platform_project, config.odoo_platform_project)
        self.assertEqual(bootstrap.odoo_src_dir, "/tmp/odoo")
        self.assertEqual(bootstrap.developing_project_dir_path, "/tmp/dev")

        new_dev = MagicMock(name="new_developing")
        new_platform = MagicMock(name="new_platform")
        bootstrap.developing_project = new_dev
        bootstrap.odoo_platform_project = new_platform
        bootstrap.odoo_src_dir = "/tmp/odoo2"
        bootstrap.developing_project_dir_path = "/tmp/dev2"
        self.assertIs(config.developing_project, new_dev)
        self.assertIs(config.odoo_platform_project, new_platform)
        self.assertEqual(config.odoo_src_dir, "/tmp/odoo2")
        self.assertEqual(config.developing_project_dir_path, "/tmp/dev2")

    def test_bootstrap_handle_secrets_session(self):
        from dev_project.secrets_providers.session import SecretsFetchSession, session_for_config

        config = MagicMock()
        bootstrap = BootstrapHandle(_assembled=config)
        session = bootstrap.secrets_session()
        self.assertIsInstance(session, SecretsFetchSession)
        self.assertIs(session, session_for_config(config))

    def test_bootstrap_handle_surfaces_inventory(self):
        self.assertEqual(
            BOOTSTRAP_HANDLE_SURFACES,
            (
                "runtime",
                "git_repos",
                "env_resolver",
                "odoo_conf",
                "pd_manager",
                "developing_project",
                "odoo_platform_project",
                "odoo_src_dir",
                "developing_project_dir_path",
                "user_env",
                "project_settings",
                "docker_layout",
                "policy",
                "arguments",
                "project_dir",
                "program_dir",
                "dockerfile_path",
                "postgres_data_local_storage",
                "service_source_paths",
                "raw_user_settings",
                "manifest_view",
                "repo_odpm_json",
                "project_name",
                "new_lock_manager",
                "compute_venv_lock_hash",
                "write_runtime_config",
                "write_runtime_config_to_path",
                "runtime_config_json_bytes",
                "to_container_config",
                "handle_git_link",
                "ensure_git_repo_symlink",
                "ensure_developing_repo_symlinks",
                "apply_nested_compatibility",
                "generate_odoo_conf_docker_data",
                "host_context",
                "skip_git_update",
                "seed_dependency_urls",
                "ensure_secrets_source",
                "resolve_base_image_ref",
                "set_env_resolver",
                "set_manifest_view",
                "secrets_session",
                "clear_runtime_config_preview_cache",
                "ensure_docker_capabilities",
            ),
        )

    def test_repo_odpm_json_shim_is_not_duplicated(self):
        repo_shims = [
            replacement
            for _slice, field, replacement in CONFIG_PROPERTY_SHIMS
            if field == "repo_odpm_json"
        ]
        self.assertEqual(repo_shims, ["host_ctx.repo_odpm_json"])

    def test_manifest_view_shim_points_at_host_ctx(self):
        manifest_shims = [
            replacement
            for _slice, field, replacement in CONFIG_PROPERTY_SHIMS
            if field == "manifest_view"
        ]
        self.assertEqual(manifest_shims, ["host_ctx.manifest_view"])

    def test_bootstrap_handle_has_no_public_config(self):
        bootstrap = BootstrapHandle(_assembled=MagicMock())
        self.assertFalse(hasattr(bootstrap, "config") and "config" in getattr(bootstrap, "__dataclass_fields__", {}))
        self.assertTrue(hasattr(bootstrap, "_assembled"))


if __name__ == "__main__":
    unittest.main()
