import unittest
from unittest.mock import MagicMock

from dev_project.inside_docker_app.odoo_checker.admin_ops import (
    OdooAdminOps,
    encrypt_odoo_password,
    ir_model_data_res_id_subquery,
)


class IrModelDataSubqueryTests(unittest.TestCase):
    def test_builds_subquery_for_xml_id(self):
        self.assertEqual(
            ir_model_data_res_id_subquery("base.user_admin"),
            " SELECT res_id FROM ir_model_data WHERE name = 'user_admin' "
            "AND module = 'base' ",
        )


class EncryptOdooPasswordTests(unittest.TestCase):
    def test_modern_odoo_uses_pbkdf2_sha512(self):
        pbkdf2 = MagicMock()
        pbkdf2.using.return_value.hash.return_value = "hashed"

        result = encrypt_odoo_password(
            "secret",
            int_odoo_version=17,
            pbkdf2_sha512=pbkdf2,
            passlib=MagicMock(),
        )

        self.assertEqual(result, "hashed")
        pbkdf2.using.assert_called_once_with(rounds=1)

    def test_legacy_odoo_uses_passlib_context(self):
        passlib = MagicMock()
        passlib.context.CryptContext.return_value.encrypt.return_value = "legacy"

        result = encrypt_odoo_password(
            "secret",
            int_odoo_version=11,
            pbkdf2_sha512=MagicMock(),
            passlib=passlib,
        )

        self.assertEqual(result, "legacy")


class OdooAdminOpsTests(unittest.TestCase):
    def test_set_admin_password_executes_update(self):
        odoo = MagicMock()
        cursor = MagicMock()
        odoo.sql_db.db_connect.return_value.cursor.return_value = cursor
        ops = OdooAdminOps(
            odoo,
            int_odoo_version=17,
            odoo_version_info=(17, 0),
            pbkdf2_sha512=MagicMock(
                using=MagicMock(
                    return_value=MagicMock(hash=MagicMock(return_value="hash"))
                )
            ),
            passlib=MagicMock(),
        )

        ops.set_admin_password(
            "demo",
            admin_login="admin@example.com",
            admin_password="secret",
        )

        odoo.sql_db.db_connect.assert_called_once_with("demo")
        cursor.execute.assert_called_once()
        cursor.commit.assert_called_once()
        sql = cursor.execute.call_args[0][0]
        self.assertIn("UPDATE res_users SET", sql)
        self.assertIn("admin@example.com", sql)


if __name__ == "__main__":
    unittest.main()
