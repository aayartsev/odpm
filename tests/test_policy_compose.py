"""Matrix A: scenario × security override → profile / binds / bootstrap."""

from __future__ import annotations

import unittest

from dev_project import constants
from dev_project.policy_compose import (
    effective_binds,
    password_bootstrap_enabled,
    resolve_security_profile,
)
from dev_project.scenario_policy import ScenarioPolicy
from dev_project.security_profiles import SecurityProfile


class PolicyComposeMatrixATests(unittest.TestCase):
    def test_matrix_a(self) -> None:
        cases: list[
            tuple[
                str,
                SecurityProfile | None,
                SecurityProfile,
                bool,
                bool,
                bool,
            ]
        ] = [
            # scenario defaults
            (
                constants.DEVELOPER_SCENARIO,
                None,
                "convenience",
                False,
                False,
                False,
            ),
            (
                constants.SERVER_SCENARIO,
                None,
                "hardened",
                True,
                True,
                True,
            ),
            (
                constants.CI_SCENARIO,
                None,
                "convenience",
                True,
                False,
                False,
            ),
            # overrides
            (
                constants.DEVELOPER_SCENARIO,
                "hardened",
                "hardened",
                True,
                True,
                True,
            ),
            (
                constants.SERVER_SCENARIO,
                "convenience",
                "convenience",
                False,
                False,
                False,
            ),
            (
                constants.CI_SCENARIO,
                "hardened",
                "hardened",
                True,
                False,
                False,
            ),
        ]
        for (
            scenario,
            override,
            expect_profile,
            expect_pg,
            expect_pub,
            expect_bootstrap,
        ) in cases:
            with self.subTest(scenario=scenario, override=override):
                profile = resolve_security_profile(scenario, override=override)
                pg, pub = effective_binds(scenario, profile)
                bootstrap = password_bootstrap_enabled(scenario, profile)
                self.assertEqual(profile, expect_profile)
                self.assertEqual(pg, expect_pg)
                self.assertEqual(pub, expect_pub)
                self.assertEqual(bootstrap, expect_bootstrap)

                policy = ScenarioPolicy.from_scenario(
                    scenario, security_profile=override
                )
                self.assertEqual(policy.security_profile, expect_profile)
                self.assertEqual(policy.bind_postgres_localhost, expect_pg)
                self.assertEqual(policy.bind_published_ports_localhost, expect_pub)
                self.assertEqual(
                    policy.should_bootstrap_odoo_password_secrets(),
                    expect_bootstrap,
                )


if __name__ == "__main__":
    unittest.main()
