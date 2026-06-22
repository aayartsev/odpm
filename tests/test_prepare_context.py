import unittest
from unittest.mock import MagicMock, patch

from dev_project.compose.generator import ComposeGenerator
from dev_project.host.cli.args import OdpmCliArgs
from dev_project.host.context import HostProjectContext
from dev_project.prepare import make_prepare_context
from dev_project.project_env import CreateProjectEnvironment
from dev_project.project_env.links import ProjectLinks
from dev_project.project_env.templates import ProjectTemplates


class PrepareContextServiceInjectionTests(unittest.TestCase):
    def test_make_prepare_context_reuses_create_project_environment_services(self):
        config = MagicMock()
        config.user_env = MagicMock()
        project_env = CreateProjectEnvironment(config)
        system_checker = MagicMock()
        args = OdpmCliArgs()

        ctx = make_prepare_context(config, project_env, system_checker, args)

        self.assertIs(ctx.templates, project_env.templates)
        self.assertIs(ctx.compose_generator, project_env.compose_generator)
        self.assertIs(ctx.links, project_env.links)

    def test_create_project_environment_caches_host_ctx(self):
        config = MagicMock()
        config.user_env = MagicMock()
        project_env = CreateProjectEnvironment(config)
        first = project_env.host_ctx
        second = project_env.host_ctx
        self.assertIs(first, second)
        self.assertIsInstance(first, HostProjectContext)

    def test_make_prepare_context_builds_services_for_generic_project_env(self):
        config = MagicMock()
        project_env = MagicMock()
        system_checker = MagicMock()
        args = OdpmCliArgs()

        ctx = make_prepare_context(config, project_env, system_checker, args)

        self.assertIsInstance(ctx.templates, ProjectTemplates)
        self.assertIsInstance(ctx.compose_generator, ComposeGenerator)
        self.assertIsInstance(ctx.links, ProjectLinks)
        self.assertIs(ctx.templates.env, project_env)
        self.assertIs(ctx.compose_generator.env, project_env)
        self.assertIs(ctx.links.env, project_env)
        self.assertIs(ctx.config, config)
        self.assertIs(ctx.project_env, project_env)
        self.assertIs(ctx.system_checker, system_checker)
        self.assertIs(ctx.args, args)
        self.assertIsInstance(ctx.host_ctx, HostProjectContext)


class PrepareStepServiceExecutionTests(unittest.TestCase):
    @patch("dev_project.project_env.templates.ProjectTemplates.generate_dockerfile")
    def test_exec_template_dockerfile_uses_ctx_templates(self, mock_generate):
        from dev_project.prepare.steps_template import exec_template_dockerfile

        config = MagicMock()
        ctx = make_prepare_context(config, MagicMock(), MagicMock(), OdpmCliArgs())
        exec_template_dockerfile(ctx)
        mock_generate.assert_called_once()

    @patch("dev_project.project_env.links.ProjectLinks.map_folders")
    def test_exec_map_folders_uses_ctx_links(self, mock_map_folders):
        from dev_project.prepare.steps_project import exec_map_folders

        ctx = make_prepare_context(MagicMock(), MagicMock(), MagicMock(), OdpmCliArgs())
        exec_map_folders(ctx)
        mock_map_folders.assert_called_once()

    @patch(
        "dev_project.compose.generator.ComposeGenerator.generate_docker_compose_file"
    )
    def test_exec_compose_generate_uses_ctx_compose_generator(self, mock_generate):
        from dev_project.prepare.steps_compose import exec_compose_generate

        ctx = make_prepare_context(MagicMock(), MagicMock(), MagicMock(), OdpmCliArgs())
        exec_compose_generate(ctx)
        mock_generate.assert_called_once()

    def test_exec_git_materialize_calls_materialize_git_repos_once(self):
        from dev_project.prepare.steps_git import exec_git_materialize

        config = MagicMock()
        git_repos = MagicMock()
        config._git_repos = git_repos
        lock_manager = MagicMock()
        lock_manager.has_platform_lock.return_value = False
        ctx = make_prepare_context(config, MagicMock(), MagicMock(), OdpmCliArgs())
        ctx.lock_manager = lock_manager

        exec_git_materialize(ctx)

        git_repos.materialize_git_repos.assert_called_once_with(skip_build_date=False)


if __name__ == "__main__":
    unittest.main()
