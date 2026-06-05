import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from dev_project import constants
from dev_project.host_project_env import CreateProjectEnvironment


class ProjectDockerignoreTests(unittest.TestCase):
    def test_ensure_project_dockerignore_writes_managed_file(self):
        with tempfile.TemporaryDirectory() as project_dir:
            config = MagicMock()
            config.project_dir = project_dir
            env = CreateProjectEnvironment(config)
            env.ensure_project_dockerignore()
            dockerignore = Path(project_dir) / ".dockerignore"
            self.assertTrue(dockerignore.is_file())
            self.assertEqual(
                dockerignore.read_text(encoding="utf-8"),
                constants.PROJECT_DOCKERIGNORE,
            )


if __name__ == "__main__":
    unittest.main()
