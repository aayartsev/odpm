"""Prepare steps and runtime evaluators must not touch raw bootstrap.config / ctx.config."""

from __future__ import annotations

import unittest
from pathlib import Path

PREPARE_DIR = Path(__file__).resolve().parents[1] / "dev_project" / "prepare"
FORBIDDEN = ("ctx.config", "bootstrap.config")


def _prepare_coupling_paths() -> list[Path]:
    paths = sorted(PREPARE_DIR.glob("steps_*.py"))
    paths.append(PREPARE_DIR / "runtime.py")
    return paths


class PrepareStepsConfigCouplingTests(unittest.TestCase):
    def test_prepare_step_modules_do_not_reference_raw_config(self):
        offenders: list[str] = []
        for path in _prepare_coupling_paths():
            text = path.read_text(encoding="utf-8")
            hits = [token for token in FORBIDDEN if token in text]
            if hits:
                offenders.append(f"{path.name}: {', '.join(hits)}")
        self.assertEqual(
            offenders,
            [],
            msg=(
                "prepare steps/runtime must use BootstrapHandle / RuntimePorts / "
                f"PrepareContext helpers: {offenders}"
            ),
        )


if __name__ == "__main__":
    unittest.main()
