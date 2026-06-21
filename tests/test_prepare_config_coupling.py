"""Prepare steps should read host state via host_ctx, not ctx.config."""

from __future__ import annotations

import unittest
from pathlib import Path

PREPARE_STEPS_DIR = Path(__file__).resolve().parents[1] / "dev_project" / "prepare"


class PrepareStepsConfigCouplingTests(unittest.TestCase):
    def test_prepare_step_modules_do_not_reference_ctx_config(self):
        offenders: list[str] = []
        for path in sorted(PREPARE_STEPS_DIR.glob("steps_*.py")):
            text = path.read_text(encoding="utf-8")
            if "ctx.config" in text:
                offenders.append(path.name)
        self.assertEqual(
            offenders,
            [],
            msg=f"prepare steps must use ctx.host_ctx / PrepareContext helpers: {offenders}",
        )


if __name__ == "__main__":
    unittest.main()
