"""Odoo database operations: backup, restore, drop, list, create."""

from __future__ import annotations

import datetime
import os
from dataclasses import dataclass
from typing import Any

DEFAULT_TIMESTAMP_FORMAT = "%Y-%m-%d_%H-%M-%S"
DEFAULT_DB_BACKUP_FORMAT = "zip"


def sanitize_backup_basename(name: str) -> str:
    result = name
    for symbol in ("-", " ", ":"):
        result = result.replace(symbol, "_")
    return result


@dataclass(frozen=True)
class DbCreationParams:
    create_demo: bool
    db_lang: str
    db_default_admin_password: str
    db_default_admin_login: str
    db_country_code: str


class OdooDbOps:
    def __init__(
        self,
        odoo: Any,
        *,
        odoo_dir: str,
        creation: DbCreationParams,
    ) -> None:
        self.odoo = odoo
        self.creation = creation
        self.backup_dir = os.path.join(os.path.dirname(odoo_dir), "backups")

    def backup_database(self, db_name: str, backup: str | bool) -> str:
        time_stamp = datetime.datetime.now().strftime(DEFAULT_TIMESTAMP_FORMAT)
        backup_filename = backup
        if isinstance(backup, bool):
            backup_filename = (
                f"{sanitize_backup_basename(db_name)}_{time_stamp}"
            )
        full_path = os.path.join(self.backup_dir, backup_filename)
        dump_stream = self.odoo.service.db.dump_db(
            db_name, None, DEFAULT_DB_BACKUP_FORMAT
        )
        os.makedirs(self.backup_dir, exist_ok=True)
        with open(full_path, "wb") as file_arch:
            for line in dump_stream.readlines():
                file_arch.write(line)
        return full_path

    def restore_database(self, db_name: str, restore_file_path: str) -> None:
        full_path = os.path.join(self.backup_dir, restore_file_path)
        self.odoo.service.db.restore_db(db_name, full_path)

    def drop_database(self, drop_db_name: str | bool, db_name: str | bool) -> None:
        target = drop_db_name
        if isinstance(drop_db_name, bool) and db_name:
            target = db_name
        if not target:
            return
        if self.odoo.service.db.exp_db_exist(target):
            self.odoo.service.db.exp_drop(target)

    def get_list_of_databases(self) -> str:
        databases = self.odoo.service.db.list_dbs(force=True)
        final_string = ""
        for database_name in databases:
            final_string += database_name + "\n"
        return final_string.strip("\n")

    def ensure_database_exists(self, db_name: str) -> None:
        if not self.odoo.service.db.exp_db_exist(db_name):
            self.odoo.service.db.exp_create_database(
                db_name,
                self.creation.create_demo,
                self.creation.db_lang,
                user_password=self.creation.db_default_admin_password,
                login=self.creation.db_default_admin_login,
                country_code=self.creation.db_country_code,
            )
