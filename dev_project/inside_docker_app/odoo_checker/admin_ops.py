"""Odoo admin user operations."""

from __future__ import annotations

from contextlib import closing
from typing import Any


def ir_model_data_res_id_subquery(xml_id: str) -> str:
    module_name, id_name = xml_id.split(".", 1)
    return (
        f" SELECT res_id FROM ir_model_data WHERE name = '{id_name}' "
        f"AND module = '{module_name}' "
    )


def encrypt_odoo_password(
    text_password: str,
    *,
    int_odoo_version: int,
    pbkdf2_sha512: Any,
    passlib: Any,
) -> str:
    if int_odoo_version not in (11, 12):
        return pbkdf2_sha512.using(rounds=1).hash(text_password)
    crypt_context = passlib.context.CryptContext(
        schemes=["pbkdf2_sha512", "plaintext"],
        deprecated=["plaintext"],
    )
    return crypt_context.encrypt(text_password)


class OdooAdminOps:
    def __init__(
        self,
        odoo: Any,
        *,
        int_odoo_version: int,
        odoo_version_info: tuple[int, ...],
        pbkdf2_sha512: Any,
        passlib: Any,
    ) -> None:
        self.odoo = odoo
        self.int_odoo_version = int_odoo_version
        self.odoo_version_info = odoo_version_info
        self.pbkdf2_sha512 = pbkdf2_sha512
        self.passlib = passlib

    def set_admin_password(
        self,
        db_name: str,
        *,
        admin_login: str,
        admin_password: str,
    ) -> None:
        password_crypt_field = "password"
        admin_xml_id = "base.user_admin"
        password_crypt = encrypt_odoo_password(
            admin_password,
            int_odoo_version=self.int_odoo_version,
            pbkdf2_sha512=self.pbkdf2_sha512,
            passlib=self.passlib,
        )
        if self.odoo_version_info[0] == 11:
            password_crypt_field = "password_crypt"
            admin_xml_id = "base.user_root"
        xml_id_query = ir_model_data_res_id_subquery(admin_xml_id)
        sql_command = f"""
        UPDATE res_users SET
            {password_crypt_field} = '{password_crypt}',
            login = '{admin_login}'
        WHERE id in ({xml_id_query});
        """
        db = self.odoo.sql_db.db_connect(db_name)
        with closing(db.cursor()) as cr:
            cr.execute(sql_command, log_exceptions=True)
            cr.commit()
