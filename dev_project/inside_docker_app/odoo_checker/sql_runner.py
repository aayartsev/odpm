"""Execute configured SQL queries against an Odoo database."""

from __future__ import annotations

from contextlib import closing
from typing import Any

from ...logging import get_module_logger

_logger = get_module_logger(__name__)


class OdooSqlRunner:
    def __init__(self, odoo: Any) -> None:
        self.odoo = odoo

    def execute_queries(self, db_name: str, queries: list[str]) -> None:
        db = self.odoo.sql_db.db_connect(db_name)
        with closing(db.cursor()) as cr:
            for query in queries:
                try:
                    cr.execute(query, log_exceptions=True)
                    cr.commit()
                except Exception:
                    _logger.warning("%s was not executed", query)
