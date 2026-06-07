"""Contract tests for prepare step registry order and ids."""

import unittest

from dev_project.prepare import PREPARE_STEPS

PREPARE_STEP_IDS = [
    "git.lock_load",
    "git.ensure_present",
    "git.materialize",
    "project.map_folders",
    "git.lock_apply",
    "template.dockerfile",
    "template.dockerignore",
    "docker.engine.check",
    "docker.ports.release",
    "template.odoo_conf",
    "compose.template",
    "compose.service",
    "compose.generate",
    "compose.validate",
    "git.checkout",
    "git.lock_collect",
    "git.lock_verify",
    "project.update_links",
]


class PrepareRegistryContractTests(unittest.TestCase):
    def test_prepare_steps_ids_and_order_unchanged(self):
        self.assertEqual([step.id for step in PREPARE_STEPS], PREPARE_STEP_IDS)

    def test_prepare_steps_have_evaluate_and_execute(self):
        for step in PREPARE_STEPS:
            self.assertTrue(callable(step.evaluate))
            self.assertTrue(callable(step.execute))


if __name__ == "__main__":
    unittest.main()
