import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dev_project.dependency_resolver import (
    DependencyDiscovery,
    NestedOdpmFragment,
    parse_oca_dependencies_line,
    read_nested_odpm_fragment,
    read_oca_dependency_urls,
    resolve_dependencies,
    resolve_dependency_urls,
)
from dev_project.config.transforms.env_substitution import EnvResolver
from dev_project.errors import ConfigError


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


class ReadNestedOdpmFragmentTests(unittest.TestCase):
    def test_missing_file_returns_none(self):
        with tempfile.TemporaryDirectory() as project_dir:
            self.assertIsNone(read_nested_odpm_fragment(project_dir))

    def test_reads_whitelisted_fields_only(self):
        with tempfile.TemporaryDirectory() as project_dir:
            manifest = Path(project_dir) / "odpm.json"
            manifest.write_text(
                json.dumps(
                    {
                        "dependencies": [
                            "https://github.com/acme/framework.git",
                            "",
                        ],
                        "requirements_txt": ["openupgradelib", "  "],
                        "odoo_version": "17.0",
                        "python_version": "3.12",
                        "odoo_git_link": "git@host:org/odoo.git",
                        "developing": "ignored",
                    }
                ),
                encoding="utf-8",
            )
            fragment = read_nested_odpm_fragment(project_dir)
            self.assertIsNotNone(fragment)
            assert fragment is not None
            self.assertEqual(
                fragment.dependencies,
                ["https://github.com/acme/framework.git"],
            )
            self.assertEqual(fragment.requirements_txt, ["openupgradelib"])
            self.assertEqual(fragment.odoo_version, "17.0")
            self.assertEqual(fragment.python_version, "3.12")
            self.assertEqual(fragment.source_path, str(manifest))

    def test_invalid_json_returns_none_and_logs_warning(self):
        with tempfile.TemporaryDirectory() as project_dir:
            (Path(project_dir) / "odpm.json").write_text("{not json", encoding="utf-8")
            with patch("dev_project.dependency_resolver._logger") as mock_logger:
                self.assertIsNone(read_nested_odpm_fragment(project_dir))
            mock_logger.warning.assert_called_once()

    def test_non_object_root_returns_none(self):
        with tempfile.TemporaryDirectory() as project_dir:
            (Path(project_dir) / "odpm.json").write_text("[1, 2]", encoding="utf-8")
            with patch("dev_project.dependency_resolver._logger") as mock_logger:
                self.assertIsNone(read_nested_odpm_fragment(project_dir))
            mock_logger.warning.assert_called_once()

    def test_invalid_list_types_treated_as_no_discovery_data(self):
        with tempfile.TemporaryDirectory() as project_dir:
            (Path(project_dir) / "odpm.json").write_text(
                json.dumps(
                    {
                        "dependencies": "not-a-list",
                        "requirements_txt": 42,
                    }
                ),
                encoding="utf-8",
            )
            self.assertIsNone(read_nested_odpm_fragment(project_dir))

    def test_empty_manifest_without_discovery_fields_returns_none(self):
        with tempfile.TemporaryDirectory() as project_dir:
            (Path(project_dir) / "odpm.json").write_text("{}", encoding="utf-8")
            self.assertIsNone(read_nested_odpm_fragment(project_dir))

    def test_expands_dependencies_env_ref_when_resolver_provided(self):
        with tempfile.TemporaryDirectory() as project_dir:
            manifest = Path(project_dir) / "odpm.json"
            manifest.write_text(
                json.dumps(
                    {
                        "dependencies": [
                            "file://${OCA_WEB_PATH}",
                            "https://github.com/OCA/sale.git 17.0",
                        ],
                        "odoo_version": "17.${ODOO_VER}",
                    }
                ),
                encoding="utf-8",
            )
            resolver = EnvResolver.from_sources(
                process_environ={},
                project_dotenv={"OCA_WEB_PATH": "/home/dev/oca/web"},
            )
            fragment = read_nested_odpm_fragment(project_dir, resolver=resolver)

            self.assertIsNotNone(fragment)
            assert fragment is not None
            self.assertEqual(
                fragment.dependencies,
                [
                    "file:///home/dev/oca/web",
                    "https://github.com/OCA/sale.git 17.0",
                ],
            )
            self.assertEqual(fragment.odoo_version, "17.${ODOO_VER}")

    def test_missing_env_var_raises_config_error_when_resolver_provided(self):
        with tempfile.TemporaryDirectory() as project_dir:
            (Path(project_dir) / "odpm.json").write_text(
                json.dumps({"dependencies": ["file://${MISSING}"]}),
                encoding="utf-8",
            )
            resolver = EnvResolver.from_sources(process_environ={}, project_dotenv={})

            with self.assertRaises(ConfigError) as ctx:
                read_nested_odpm_fragment(project_dir, resolver=resolver)

            self.assertIn("MISSING", str(ctx.exception))
            self.assertIn("dependencies", str(ctx.exception))

    def test_without_resolver_leaves_env_refs_literal(self):
        with tempfile.TemporaryDirectory() as project_dir:
            (Path(project_dir) / "odpm.json").write_text(
                json.dumps({"dependencies": ["file://${OCA_WEB_PATH}"]}),
                encoding="utf-8",
            )
            fragment = read_nested_odpm_fragment(project_dir)

            self.assertIsNotNone(fragment)
            assert fragment is not None
            self.assertEqual(
                fragment.dependencies,
                ["file://${OCA_WEB_PATH}"],
            )


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


class ResolveDependenciesTests(unittest.TestCase):
    def test_transitive_nested_chain_with_requirements(self):
        url_a = "https://github.com/acme/A.git"
        url_b = "https://github.com/acme/B.git"
        graph = {
            url_a: DependencyDiscovery(
                urls=[url_b],
                requirements=["openupgradelib"],
                nested_fragment=NestedOdpmFragment(
                    dependencies=[url_b],
                    requirements_txt=["openupgradelib"],
                    odoo_version="17.0",
                    python_version="3.12",
                    source_path="/tmp/a/odpm.json",
                ),
            ),
            url_b: DependencyDiscovery(
                requirements=["xlrd"],
                nested_fragment=NestedOdpmFragment(
                    dependencies=[],
                    requirements_txt=["xlrd"],
                    odoo_version=None,
                    python_version=None,
                    source_path="/tmp/b/odpm.json",
                ),
            ),
        }

        result = resolve_dependencies([url_a], graph.get)

        self.assertEqual(result.urls, [url_a, url_b])
        self.assertEqual(result.transitive_requirements, ["openupgradelib", "xlrd"])
        self.assertEqual(len(result.nested_fragments), 2)

    def test_combined_oca_and_nested_urls_in_one_discovery(self):
        url_a = "https://github.com/acme/A.git"
        url_b = "https://github.com/OCA/B.git"
        url_c = "https://github.com/OCA/C.git"

        def discover(url: str) -> DependencyDiscovery:
            if url == url_a:
                return DependencyDiscovery(
                    urls=[url_b, url_c],
                    requirements=["requests"],
                )
            if url == url_b:
                return DependencyDiscovery(urls=[url_c])
            return DependencyDiscovery()

        result = resolve_dependencies([url_a], discover)

        self.assertEqual(result.urls, [url_a, url_b, url_c])
        self.assertEqual(result.transitive_requirements, ["requests"])

    def test_requirements_deduped_in_bfs_order(self):
        url_a = "https://github.com/acme/A.git"
        url_b = "https://github.com/acme/B.git"

        def discover(url: str) -> DependencyDiscovery:
            if url == url_a:
                return DependencyDiscovery(
                    urls=[url_b],
                    requirements=["openupgradelib", "requests"],
                )
            if url == url_b:
                return DependencyDiscovery(requirements=["requests", "xlrd"])
            return DependencyDiscovery()

        result = resolve_dependencies([url_a], discover)

        self.assertEqual(
            result.transitive_requirements,
            ["openupgradelib", "requests", "xlrd"],
        )

    def test_nested_fragments_deduped_by_source_path(self):
        fragment = NestedOdpmFragment(
            dependencies=[],
            requirements_txt=["pkg"],
            odoo_version=None,
            python_version=None,
            source_path="/tmp/shared/odpm.json",
        )
        url = "https://github.com/acme/A.git"

        def discover(_url: str) -> DependencyDiscovery:
            return DependencyDiscovery(requirements=["pkg"], nested_fragment=fragment)

        result = resolve_dependencies([url, url], discover)

        self.assertEqual(result.urls, [url])
        self.assertEqual(result.nested_fragments, [fragment])


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

            def handle_git_link(dependency_string, materialize=False, system_type="standart"):
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
            config.skip_git_update.return_value = False
            config.developing_project = MagicMock(project_path=str(developing))
            config.handle_git_link = MagicMock(side_effect=handle_git_link)

            resolved = self._make_env(config).links._resolve_dependencies()

            self.assertEqual(resolved.urls, [url_a, url_b])
            config.handle_git_link.assert_any_call(url_a, materialize=True)
            config.handle_git_link.assert_any_call(url_b, materialize=True)

    def test_resolve_dependencies_warns_when_dependency_not_cloned(self):
        config = MagicMock()
        config.dependencies = ["https://github.com/OCA/missing.git"]
        config.use_oca_dependencies = True
        config.skip_git_update.return_value = False
        config.developing_project = MagicMock(project_path="")
        missing = MagicMock(is_cloned=False, project_path="")
        config.handle_git_link = MagicMock(return_value=missing)

        env = self._make_env(config)
        with patch(
            "dev_project.project_env.dependency_materializer._logger"
        ) as mock_logger:
            resolved = env.links._resolve_dependencies()

        self.assertEqual(resolved.urls, ["https://github.com/OCA/missing.git"])
        mock_logger.warning.assert_called_once()


if __name__ == "__main__":
    unittest.main()
