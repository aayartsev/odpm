import unittest
from unittest.mock import MagicMock

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


if __name__ == "__main__":
    unittest.main()
