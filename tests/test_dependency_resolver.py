import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dev_project.dependency_resolver import (
    parse_oca_dependencies_line,
    read_oca_dependency_urls,
    resolve_dependency_urls,
)


class ParseOcaDependenciesLineTests(unittest.TestCase):
    def test_module_name_expands_to_github_url(self):
        self.assertEqual(
            parse_oca_dependencies_line("sale-workflow"),
            "https://github.com/OCA/sale-workflow.git",
        )

    def test_full_github_url_passthrough(self):
        url = "https://github.com/OCA/account-financial-tools.git"
        self.assertEqual(parse_oca_dependencies_line(url), url)

    def test_comment_and_empty_lines_skipped(self):
        self.assertIsNone(parse_oca_dependencies_line("# comment"))
        self.assertIsNone(parse_oca_dependencies_line(""))
        self.assertIsNone(parse_oca_dependencies_line("   "))


class ReadOcaDependencyUrlsTests(unittest.TestCase):
    def test_reads_file_like_real_oca_dependencies_txt(self):
        with tempfile.TemporaryDirectory() as project_dir:
            oca_file = Path(project_dir) / "oca_dependencies.txt"
            oca_file.write_text(
                "# OCA deps for project\n"
                "sale-workflow\n"
                "https://github.com/OCA/stock-logistics-workflow.git\n"
                "\n"
                "# partner-contact\n",
                encoding="utf-8",
            )
            urls = read_oca_dependency_urls(project_dir)
            self.assertEqual(
                urls,
                [
                    "https://github.com/OCA/sale-workflow.git",
                    "https://github.com/OCA/stock-logistics-workflow.git",
                ],
            )

    def test_missing_file_returns_empty_list(self):
        with tempfile.TemporaryDirectory() as project_dir:
            self.assertEqual(read_oca_dependency_urls(project_dir), [])


class ResolveDependencyUrlsTests(unittest.TestCase):
    def test_transitive_oca_chain_resolved_in_one_pass(self):
        """A -> B -> C must all appear without a second odpm run."""
        graph = {
            "https://github.com/OCA/A.git": [
                "https://github.com/OCA/B.git",
            ],
            "https://github.com/OCA/B.git": [
                "https://github.com/OCA/C.git",
            ],
            "https://github.com/OCA/C.git": [],
        }

        def get_oca(url: str) -> list[str]:
            return graph.get(url, [])

        resolved = resolve_dependency_urls(
            ["https://github.com/OCA/A.git"],
            get_oca,
        )
        self.assertEqual(
            resolved,
            [
                "https://github.com/OCA/A.git",
                "https://github.com/OCA/B.git",
                "https://github.com/OCA/C.git",
            ],
        )

    def test_developing_project_extras_processed_like_legacy_append(self):
        """URLs from developing oca_dependencies.txt follow odpm.json seeds."""
        calls: list[str] = []

        def get_oca(url: str) -> list[str]:
            calls.append(url)
            if url.endswith("sale-workflow.git"):
                return ["https://github.com/OCA/stock-logistics-workflow.git"]
            return []

        resolved = resolve_dependency_urls(
            ["https://github.com/OCA/account-financial-tools.git"],
            get_oca,
            initial_extra_urls=["https://github.com/OCA/sale-workflow.git"],
        )
        self.assertEqual(
            resolved,
            [
                "https://github.com/OCA/account-financial-tools.git",
                "https://github.com/OCA/sale-workflow.git",
                "https://github.com/OCA/stock-logistics-workflow.git",
            ],
        )
        self.assertEqual(
            calls,
            [
                "https://github.com/OCA/account-financial-tools.git",
                "https://github.com/OCA/sale-workflow.git",
                "https://github.com/OCA/stock-logistics-workflow.git",
            ],
        )

    def test_duplicates_and_cycles_do_not_inflate_list(self):
        def get_oca(url: str) -> list[str]:
            if url.endswith("A.git"):
                return ["https://github.com/OCA/B.git"]
            if url.endswith("B.git"):
                return ["https://github.com/OCA/A.git"]
            return []

        resolved = resolve_dependency_urls(
            ["https://github.com/OCA/A.git", "https://github.com/OCA/A.git"],
            get_oca,
        )
        self.assertEqual(
            resolved,
            ["https://github.com/OCA/A.git", "https://github.com/OCA/B.git"],
        )

    def test_without_oca_callback_returns_seeds_only(self):
        resolved = resolve_dependency_urls(
            ["https://github.com/OCA/X.git"],
            lambda _url: [],
        )
        self.assertEqual(resolved, ["https://github.com/OCA/X.git"])


class ResolveDependenciesIntegrationTests(unittest.TestCase):
    """Host-layer _resolve_dependencies() with real oca_dependencies.txt on disk."""

    def _make_env(self, config):
        from dev_project.project_env import CreateProjectEnvironment

        env = CreateProjectEnvironment(config)
        env._links.checkout_project = MagicMock()
        return env

    def test_resolve_dependencies_discovers_transitive_oca_on_disk(self):
        with tempfile.TemporaryDirectory() as base:
            dep_a = Path(base) / "dep_a"
            dep_b = Path(base) / "dep_b"
            developing = Path(base) / "developing"
            dep_a.mkdir()
            dep_b.mkdir()
            developing.mkdir()
            (dep_a / "oca_dependencies.txt").write_text(
                "https://github.com/OCA/B.git\n",
                encoding="utf-8",
            )

            url_a = "https://github.com/OCA/A.git"
            url_b = "https://github.com/OCA/B.git"

            def handle_git_link(dependency_string, system_type="standart"):
                link = MagicMock()
                link.is_cloned = dependency_string in (url_a, url_b)
                if dependency_string == url_a:
                    link.project_path = str(dep_a)
                elif dependency_string == url_b:
                    link.project_path = str(dep_b)
                else:
                    link.project_path = ""
                return link

            config = MagicMock()
            config.dependencies = [url_a]
            config.use_oca_dependencies = True
            config.developing_project = MagicMock(project_path=str(developing))
            config.handle_git_link = MagicMock(side_effect=handle_git_link)

            resolved = self._make_env(config)._resolve_dependencies()

            self.assertEqual(resolved, [url_a, url_b])
            config.handle_git_link.assert_any_call(url_a)
            config.handle_git_link.assert_any_call(url_b)

    def test_resolve_dependencies_warns_when_dependency_not_cloned(self):
        config = MagicMock()
        config.dependencies = ["https://github.com/OCA/missing.git"]
        config.use_oca_dependencies = True
        config.developing_project = MagicMock(project_path="")
        missing = MagicMock(is_cloned=False, project_path="")
        config.handle_git_link = MagicMock(return_value=missing)

        env = self._make_env(config)
        with patch(
            "dev_project.project_env.links._logger"
        ) as mock_logger:
            resolved = env._resolve_dependencies()

        self.assertEqual(resolved, ["https://github.com/OCA/missing.git"])
        mock_logger.warning.assert_called_once()


if __name__ == "__main__":
    unittest.main()
