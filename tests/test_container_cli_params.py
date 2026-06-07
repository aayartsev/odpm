"""Container checker CLI flag names must stay in sync with host CLI params."""

from __future__ import annotations

import unittest

from dev_project.host.cli import params as host_params
from dev_project.inside_docker_app import params as container_params


def _public_param_names(module) -> tuple[str, ...]:
    return tuple(
        name
        for name in dir(module)
        if name.isupper() and not name.startswith("_")
    )


class ContainerCliParamsSyncTests(unittest.TestCase):
    def test_checker_flag_names_match_host_cli_params(self):
        for name in _public_param_names(container_params):
            with self.subTest(name=name):
                self.assertTrue(
                    hasattr(host_params, name),
                    f"host.cli.params missing {name} used by container checker",
                )
                self.assertEqual(
                    getattr(container_params, name),
                    getattr(host_params, name),
                )


if __name__ == "__main__":
    unittest.main()
