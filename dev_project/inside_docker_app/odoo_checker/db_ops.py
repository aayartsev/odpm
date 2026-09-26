"""Odoo database operations: backup, restore, drop, list, create."""

from __future__ import annotations

import datetime
import os
import shutil
from contextlib import closing
from dataclasses import dataclass
from typing import Any

from ...logging import get_module_logger
from ..exceptions import PostgresError

DEFAULT_TIMESTAMP_FORMAT = "%Y-%m-%d_%H-%M-%S"
DEFAULT_DB_BACKUP_FORMAT = "zip"

_logger = get_module_logger(__name__)


def sanitize_backup_basename(name: str) -> str:
    result = name
    for symbol in ("-", " ", ":"):
        result = result.replace(symbol, "_")
    return result


def normalize_country_code(value: Any) -> str | None:
    """Map empty / falsy / ``false`` country codes to ``None`` for Odoo create()."""
    if value is None or value is False:
        return None
    if isinstance(value, bool):
        return None
    text = str(value).strip()
    if not text or text.lower() == "false":
        return None
    return text


@dataclass(frozen=True)
class DbCreationParams:
    create_demo: bool
    db_lang: str
    db_default_admin_password: str
    db_default_admin_login: str
    db_country_code: str | bool | None


class OdooDbOps:
    def __init__(
        self,
        odoo: Any,
        *,
        odoo_dir: str,
        creation: DbCreationParams,
        int_odoo_version: int,
    ) -> None:
        self.odoo = odoo
        self.creation = creation
        self.int_odoo_version = int_odoo_version
        self.backup_dir = os.path.join(os.path.dirname(odoo_dir), "backups")

    @property
    def _use_modules_db(self) -> bool:
        return self.int_odoo_version >= 20

    def _db_exist(self, db_name: str) -> bool:
        if self._use_modules_db:
            return bool(self.odoo.modules.db.exist(db_name))
        return bool(self.odoo.service.db.exp_db_exist(db_name))

    def _db_create(self, db_name: str) -> None:
        country_code = normalize_country_code(self.creation.db_country_code)
        if self._use_modules_db:
            self.odoo.modules.db.create(
                db_name,
                demo=self.creation.create_demo,
                lang=self.creation.db_lang,
                user_password=self.creation.db_default_admin_password,
                user_login=self.creation.db_default_admin_login,
                country_code=country_code,
            )
            return
        self.odoo.service.db.exp_create_database(
            db_name,
            self.creation.create_demo,
            self.creation.db_lang,
            user_password=self.creation.db_default_admin_password,
            login=self.creation.db_default_admin_login,
            country_code=country_code,
        )

    def _db_drop(self, db_name: str) -> bool:
        """Drop database via Odoo API.

        For Odoo < 20 returns ``exp_drop`` result (False may mean skipped).
        For Odoo >= 20 calls ``modules.db.drop`` and returns True on success.
        """
        if self._use_modules_db:
            self.odoo.modules.db.drop(db_name)
            return True
        return bool(self.odoo.service.db.exp_drop(db_name))

    def _db_list(self) -> list[str]:
        if self._use_modules_db:
            return list(self.odoo.modules.db.list_dbs(force=True))
        return list(self.odoo.service.db.list_dbs(force=True))

    def _db_dump(self, db_name: str, full_path: str) -> None:
        os.makedirs(self.backup_dir, exist_ok=True)
        if self._use_modules_db:
            self.odoo.modules.db.dump(
                db_name,
                full_path,
                backup_format=DEFAULT_DB_BACKUP_FORMAT,
            )
            return
        dump_stream = self.odoo.service.db.dump_db(
            db_name, None, DEFAULT_DB_BACKUP_FORMAT
        )
        with open(full_path, "wb") as file_arch:
            for line in dump_stream.readlines():
                file_arch.write(line)

    def _db_restore(self, db_name: str, full_path: str) -> None:
        if self._use_modules_db:
            self.odoo.modules.db.restore(db_name, full_path)
            return
        self.odoo.service.db.restore_db(db_name, full_path)

    def backup_database(self, db_name: str, backup: str | bool) -> str:
        time_stamp = datetime.datetime.now().strftime(DEFAULT_TIMESTAMP_FORMAT)
        backup_filename = backup
        if isinstance(backup, bool):
            backup_filename = (
                f"{sanitize_backup_basename(db_name)}_{time_stamp}"
            )
        full_path = os.path.join(self.backup_dir, backup_filename)
        self._db_dump(db_name, full_path)
        return full_path

    def restore_database(self, db_name: str, restore_file_path: str) -> None:
        full_path = os.path.join(self.backup_dir, restore_file_path)
        self._db_restore(db_name, full_path)

    def drop_database(self, drop_db_name: str | bool, db_name: str | bool) -> None:
        target = drop_db_name
        if isinstance(drop_db_name, bool) and db_name:
            target = db_name
        if not target or not isinstance(target, str):
            return
        if not self._db_exist(target):
            return

        if self._use_modules_db:
            try:
                self._db_drop(target)
            except Exception as exc:
                raise PostgresError(
                    f"Could not drop database {target!r}: {exc}"
                ) from exc
            if self._db_exist(target):
                raise PostgresError(
                    f"Could not drop database {target!r}; "
                    "check PostgreSQL ownership and permissions."
                )
            return

        if not self._db_drop(target):
            _logger.info(
                "Odoo exp_drop skipped database %s (likely wrong owner in list_dbs); "
                "attempting direct PostgreSQL drop.",
                target,
            )

        if self._db_exist(target):
            self._force_drop_database(target)

        if self._db_exist(target):
            raise PostgresError(
                f"Could not drop database {target!r}; "
                "check PostgreSQL ownership and permissions."
            )

    def _force_drop_database(self, db_name: str) -> None:
        """Drop via PostgreSQL when Odoo exp_drop skips non-owned databases (< 20)."""
        db_service = self.odoo.service.db
        _logger.info("Dropping database %s via PostgreSQL", db_name)

        self.odoo.modules.registry.Registry.delete(db_name)
        self.odoo.sql_db.close_db(db_name)

        db = self.odoo.sql_db.db_connect("postgres")
        with closing(db.cursor()) as cr:
            cr._cnx.autocommit = True
            db_service._drop_conn(cr, db_name)
            try:
                cr.execute(
                    self.odoo.tools.SQL(
                        "DROP DATABASE %s",
                        db_service.database_identifier(cr, db_name),
                    )
                )
            except Exception as exc:
                raise PostgresError(
                    f"Could not drop database {db_name!r}: {exc}"
                ) from exc

        filestore = self.odoo.tools.config.filestore(db_name)
        if os.path.exists(filestore):
            shutil.rmtree(filestore)

    def get_list_of_databases(self) -> str:
        databases = self._db_list()
        final_string = ""
        for database_name in databases:
            final_string += database_name + "\n"
        return final_string.strip("\n")

    def ensure_database_exists(self, db_name: str) -> None:
        if not self._db_exist(db_name):
            self._db_create(db_name)
