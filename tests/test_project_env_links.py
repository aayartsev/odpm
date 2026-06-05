import unittest
from unittest.mock import MagicMock

from dev_project.project_env.links import ProjectLinks


class ProjectLinksDependencyTests(unittest.TestCase):
    def test_resolve_dependencies_skips_oca_when_no_git_update(self):
        env = MagicMock()
        env.config = MagicMock()
        env.config.dependencies = ["https://github.com/OCA/partner-contact.git"]
        env.config.use_oca_dependencies = True
        env.config.skip_git_update.return_value = True

        resolved = ProjectLinks(env)._resolve_dependencies()

        self.assertEqual(
            resolved,
            ["https://github.com/OCA/partner-contact.git"],
        )


if __name__ == "__main__":
    unittest.main()
