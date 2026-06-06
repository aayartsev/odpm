import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from dev_project.dependency_resolver import DependencyResolutionResult, NestedOdpmFragment
from dev_project.project_env.dependency_materializer import DependencyMaterializer


class DependencyMaterializerResolveTests(unittest.TestCase):
    def test_resolve_skips_discovery_when_no_git_update(self):
        config = MagicMock()
        config.dependencies = ["https://github.com/OCA/partner-contact.git"]
        config.use_oca_dependencies = True
        config.skip_git_update.return_value = True
        checkout_fn = MagicMock()

        resolved = DependencyMaterializer(
            config,
            checkout_fn=checkout_fn,
        ).resolve()

        self.assertEqual(
            resolved.urls,
            ["https://github.com/OCA/partner-contact.git"],
        )
        self.assertEqual(resolved.transitive_requirements, [])
        checkout_fn.assert_not_called()

    def test_resolve_skips_discovery_when_oca_disabled(self):
        config = MagicMock()
        config.dependencies = ["https://github.com/acme/A.git"]
        config.use_oca_dependencies = False
        config.skip_git_update.return_value = False
        checkout_fn = MagicMock()

        resolved = DependencyMaterializer(config, checkout_fn=checkout_fn).resolve()

        self.assertEqual(resolved.urls, config.dependencies)
        checkout_fn.assert_not_called()

    def test_apply_to_config_updates_dependencies_and_requirements(self):
        config = MagicMock()
        fragment = NestedOdpmFragment(
            dependencies=[],
            requirements_txt=["requests"],
            odoo_version="17.0",
            python_version="3.12",
            source_path="/tmp/odpm.json",
        )
        resolution = DependencyResolutionResult(
            urls=["https://github.com/acme/A.git", "https://github.com/acme/B.git"],
            transitive_requirements=["requests"],
            nested_fragments=[fragment],
        )

        DependencyMaterializer(config, checkout_fn=MagicMock()).apply_to_config(
            resolution
        )

        self.assertEqual(config.dependencies, resolution.urls)
        config.apply_transitive_requirements.assert_called_once_with(
            ["requests"],
            nested_fragments=[fragment],
        )

    def test_apply_to_config_skips_requirements_when_empty(self):
        config = MagicMock()
        resolution = DependencyResolutionResult(
            urls=["https://github.com/acme/A.git"],
            transitive_requirements=[],
            nested_fragments=[],
        )

        DependencyMaterializer(config, checkout_fn=MagicMock()).apply_to_config(
            resolution
        )

        self.assertEqual(config.dependencies, resolution.urls)
        config.apply_transitive_requirements.assert_not_called()


class DependencyMaterializerDiscoveryTests(unittest.TestCase):
    def test_discover_extensions_reads_nested_odpm_json(self):
        with tempfile.TemporaryDirectory() as base:
            dep_a = Path(base) / "dep_a"
            dep_b = Path(base) / "dep_b"
            dep_a.mkdir()
            dep_b.mkdir()
            (dep_a / "odpm.json").write_text(
                json.dumps(
                    {
                        "dependencies": ["https://github.com/acme/B.git"],
                        "requirements_txt": ["openupgradelib"],
                    }
                ),
                encoding="utf-8",
            )

            url_a = "https://github.com/acme/A.git"
            url_b = "https://github.com/acme/B.git"

            def handle_git_link(dependency_string, materialize=False):
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
            config.developing_project = MagicMock(project_path="")
            config.handle_git_link = MagicMock(side_effect=handle_git_link)
            checkout_fn = MagicMock()

            result = DependencyMaterializer(
                config,
                checkout_fn=checkout_fn,
            ).resolve()

            self.assertEqual(result.urls, [url_a, url_b])
            self.assertEqual(result.transitive_requirements, ["openupgradelib"])
            config.handle_git_link.assert_any_call(url_a, materialize=True)
            checkout_fn.assert_called()


if __name__ == "__main__":
    unittest.main()
