import importlib
import unittest
from unittest.mock import patch

from dev_project.inside_docker_app.exceptions import VenvError


class VenvImportSmokeTests(unittest.TestCase):
    def _venv_import_smoke_module(self):
        return importlib.import_module("dev_project.inside_docker_app.venv_import_smoke")

    def test_verify_venv_import_smoke_succeeds_when_modules_importable(self):
        module = self._venv_import_smoke_module()
        with patch.object(module.importlib, "import_module") as mock_import:
            self.assertTrue(
                module.verify_venv_import_smoke(raise_on_failure=False)
            )
            self.assertGreater(mock_import.call_count, 0)

    def test_verify_venv_import_smoke_raises_when_module_missing(self):
        module = self._venv_import_smoke_module()

        def _import(name: str):
            if name == "decorator":
                raise ImportError("no decorator")
            return object()

        with patch.object(module.importlib, "import_module", side_effect=_import):
            with self.assertRaises(VenvError) as ctx:
                module.verify_venv_import_smoke()
            self.assertIn("decorator", str(ctx.exception))

    def test_verify_venv_import_smoke_returns_false_without_raise(self):
        module = self._venv_import_smoke_module()
        with patch.object(
            module.importlib,
            "import_module",
            side_effect=ImportError("missing"),
        ):
            self.assertFalse(
                module.verify_venv_import_smoke(raise_on_failure=False)
            )


if __name__ == "__main__":
    unittest.main()
