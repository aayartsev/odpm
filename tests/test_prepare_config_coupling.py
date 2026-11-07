"""Prepare steps must not touch raw bootstrap.config / ctx.config."""

from __future__ import annotations

import unittest
from pathlib import Path

PREPARE_STEPS_DIR = Path(__file__).resolve().parents[1] / "dev_project" / "prepare"
FORBIDDEN = ("ctx.config", "bootstrap.config")


class PrepareStepsConfigCouplingTests(unittest.TestCase):
    def test_prepare_step_modules_do_not_reference_raw_config(self):
        offenders: list[str] = []
        for path in sorted(PREPARE_STEPS_DIR.glob("steps_*.py")):
            text = path.read_text(encoding="utf-8")
            hits = [token for token in FORBIDDEN if token in text]
            if hits:
                offenders.append(f"{path.name}: {', '.join(hits)}")
        self.assertEqual(
            offenders,
            [],
            msg=(
                "prepare steps must use BootstrapHandle / PrepareContext helpers: "
                f"{offenders}"
            ),
        )


if __name__ == "__main__":
    unittest.main()
