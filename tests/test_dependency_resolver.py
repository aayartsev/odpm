import sys
import tempfile
import unittest
from pathlib import Path

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


if __name__ == "__main__":
    unittest.main()
