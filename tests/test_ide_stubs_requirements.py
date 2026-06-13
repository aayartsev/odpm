import unittest

from dev_project import constants
from dev_project.ide_stubs import (
    is_odoo_stubs_requirement,
    normalize_odoo_stubs_requirements,
    odoo_stubs_pip_requirement,
)
from dev_project.ide_stubs.requirements import odoo_stubs_git_branch


class OdooStubsRequirementsTests(unittest.TestCase):
    def test_is_odoo_stubs_requirement_recognizes_real_pip_specs(self):
        self.assertTrue(is_odoo_stubs_requirement("odoo-stubs==1.0"))
        self.assertTrue(is_odoo_stubs_requirement("odoo_stubs>=0.1"))
        self.assertTrue(
            is_odoo_stubs_requirement(
                "odoo-stubs @ git+https://github.com/odoo-ide/odoo-stubs.git@17.0"
            )
        )
        self.assertFalse(is_odoo_stubs_requirement("requests==2.31.0"))

    def test_odoo_stubs_git_branch_by_version(self):
        self.assertEqual(odoo_stubs_git_branch("16.0"), "16.0")
        self.assertEqual(odoo_stubs_git_branch("17.0"), "17.0")
        self.assertEqual(odoo_stubs_git_branch("18.0"), "18.0")
        self.assertIsNone(odoo_stubs_git_branch("19.0"))
        self.assertIsNone(odoo_stubs_git_branch("20.0"))
        self.assertIsNone(odoo_stubs_git_branch(""))

    def test_odoo_stubs_pip_requirement_for_supported_odoo(self):
        expected = (
            "odoo-stubs @ git+"
            f"{constants.ODOO_STUBS_GIT_REPO}@17.0"
        )
        self.assertEqual(odoo_stubs_pip_requirement("17.0"), expected)

    def test_odoo_stubs_pip_requirement_skips_odoo_19(self):
        self.assertIsNone(odoo_stubs_pip_requirement("19.0"))

    def test_normalize_adds_pinned_stubs_for_developer(self):
        normalized = normalize_odoo_stubs_requirements(
            ["pre-commit"],
            odoo_version="17.0",
            install_odoo_stubs=True,
        )
        self.assertIn("pre-commit", normalized)
        self.assertEqual(
            sum(1 for req in normalized if is_odoo_stubs_requirement(req)),
            1,
        )
        self.assertEqual(normalized[-1], odoo_stubs_pip_requirement("17.0"))

    def test_normalize_strips_user_stubs_and_replaces(self):
        normalized = normalize_odoo_stubs_requirements(
            ["odoo-stubs==0.0.1", "requests==2.31.0"],
            odoo_version="18.0",
            install_odoo_stubs=True,
        )
        self.assertNotIn("odoo-stubs==0.0.1", normalized)
        self.assertIn("requests==2.31.0", normalized)
        self.assertIn(odoo_stubs_pip_requirement("18.0"), normalized)

    def test_normalize_skips_when_disabled(self):
        normalized = normalize_odoo_stubs_requirements(
            ["odoo-stubs==1.0", "requests==2.31.0"],
            odoo_version="17.0",
            install_odoo_stubs=False,
        )
        self.assertEqual(normalized, ["requests==2.31.0"])

    def test_normalize_skips_for_odoo_19_even_when_enabled(self):
        normalized = normalize_odoo_stubs_requirements(
            ["pre-commit"],
            odoo_version="19.0",
            install_odoo_stubs=True,
        )
        self.assertEqual(normalized, ["pre-commit"])
        self.assertFalse(any(is_odoo_stubs_requirement(req) for req in normalized))


if __name__ == "__main__":
    unittest.main()
