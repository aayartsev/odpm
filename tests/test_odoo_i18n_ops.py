import os
import tempfile
import unittest
from unittest.mock import MagicMock

from dev_project.inside_docker_app.odoo_checker.i18n_ops import OdooI18nOps


class OdooI18nOpsTests(unittest.TestCase):
    def test_export_po_files_writes_po_and_pot(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            addons_dir = os.path.join(tmp_dir, "extra-addons")
            module_dir = os.path.join(addons_dir, "sale")
            os.makedirs(module_dir)
            odoo = MagicMock()
            cursor = MagicMock()
            odoo.sql_db.db_connect.return_value.cursor.return_value = cursor
            odoo.tools.trans_export.side_effect = (
                lambda _lang, _modules, buf, _fmt, _cr: buf.write(b"PO")
            )
            ops = OdooI18nOps(odoo, int_odoo_version=17)

            ops.export_po_files(
                "demo",
                "ru_RU",
                ["sale"],
                [addons_dir],
            )

            self.assertTrue(os.path.isfile(os.path.join(module_dir, "i18n", "ru.po")))
            self.assertTrue(os.path.isfile(os.path.join(module_dir, "i18n", "sale.pot")))

    def test_export_po_files_uses_translate_module_for_odoo_18(self):
        odoo = MagicMock()
        cursor = MagicMock()
        odoo.sql_db.db_connect.return_value.cursor.return_value = cursor
        with tempfile.TemporaryDirectory() as tmp_dir:
            addons_dir = os.path.join(tmp_dir, "extra-addons")
            os.makedirs(os.path.join(addons_dir, "sale"))
            odoo.tools.translate.trans_export.side_effect = (
                lambda _lang, _modules, buf, _fmt, _cr: buf.write(b"PO")
            )
            ops = OdooI18nOps(odoo, int_odoo_version=18)

            ops.export_po_files("demo", "ru_RU", ["sale"], [addons_dir])

            odoo.tools.translate.trans_export.assert_called()


if __name__ == "__main__":
    unittest.main()
