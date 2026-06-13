import unittest

from dev_project.config.nested_compatibility import collect_nested_compatibility_issues
from dev_project.dependency_resolver import NestedOdpmFragment


class CollectNestedCompatibilityIssuesTests(unittest.TestCase):
    def _fragment(self, **kwargs) -> NestedOdpmFragment:
        defaults = {
            "dependencies": [],
            "requirements_txt": [],
            "odoo_version": None,
            "python_version": None,
            "source_path": "/tmp/framework/odpm.json",
        }
        defaults.update(kwargs)
        return NestedOdpmFragment(**defaults)

    def test_no_issues_when_nested_versions_match(self):
        fragment = self._fragment(odoo_version="17.0", python_version="3.12")
        self.assertEqual(
            collect_nested_compatibility_issues("17.0", "3.12", [fragment]),
            [],
        )

    def test_no_issues_when_nested_versions_omitted(self):
        fragment = self._fragment()
        self.assertEqual(
            collect_nested_compatibility_issues("17.0", "3.12", [fragment]),
            [],
        )

    def test_odoo_version_mismatch_reported(self):
        fragment = self._fragment(odoo_version="19.0")
        issues = collect_nested_compatibility_issues("17.0", "3.12", [fragment])
        self.assertEqual(len(issues), 1)
        self.assertIn("odoo_version", issues[0])
        self.assertIn("/tmp/framework/odpm.json", issues[0])

    def test_python_version_mismatch_reported(self):
        fragment = self._fragment(python_version="3.11")
        issues = collect_nested_compatibility_issues("17.0", "3.12", [fragment])
        self.assertEqual(len(issues), 1)
        self.assertIn("python_version", issues[0])

    def test_odoo_version_int_matches_float_host(self):
        fragment = self._fragment(odoo_version=17)
        self.assertEqual(
            collect_nested_compatibility_issues("17.0", "3.12", [fragment]),
            [],
        )


if __name__ == "__main__":
    unittest.main()
