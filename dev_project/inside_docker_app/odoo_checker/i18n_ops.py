"""Export PO/POT translation files for Odoo modules."""

from __future__ import annotations

import io
import os
from contextlib import closing
from typing import Any, Iterable

from ..logger import get_module_logger

_logger = get_module_logger(__name__)


class OdooI18nOps:
    def __init__(self, odoo: Any, *, int_odoo_version: int) -> None:
        self.odoo = odoo
        self.int_odoo_version = int_odoo_version

    def export_po_files(
        self,
        db_name: str,
        lang: str,
        module_names: Iterable[str],
        docker_dirs_with_addons: Iterable[str],
    ) -> None:
        db = self.odoo.sql_db.db_connect(db_name)
        for module_name in module_names:
            module_path = ""
            for addons_dir in docker_dirs_with_addons:
                candidate = os.path.join(addons_dir, module_name)
                if os.path.exists(candidate):
                    module_path = candidate
                    break
            i18n_path = os.path.join(module_path, "i18n")
            if not os.path.exists(i18n_path):
                os.mkdir(i18n_path)
            for file_ext in ("po", "pot"):
                with closing(io.BytesIO()) as buf:
                    with closing(db.cursor()) as cr:
                        env = self.odoo.api.Environment(
                            cr, self.odoo.SUPERUSER_ID, {}
                        )
                        export_lang = lang
                        file_name = lang.split("_")[0]
                        if file_ext == "pot":
                            export_lang = False
                            file_name = module_name
                        if self.int_odoo_version <= 17:
                            self.odoo.tools.trans_export(
                                export_lang, [module_name], buf, "po", cr
                            )
                        elif self.int_odoo_version == 18:
                            self.odoo.tools.translate.trans_export(
                                export_lang, [module_name], buf, "po", cr
                            )
                        else:
                            self.odoo.tools.translate.trans_export(
                                export_lang, [module_name], buf, "po", env
                            )
                        content = buf.getvalue()
                        full_file_path = os.path.join(
                            i18n_path, f"{file_name}.{file_ext}"
                        )
                        with open(full_file_path, "wb") as file_to_write:
                            file_to_write.write(content)
            _logger.info(
                "PO file with translation at %s language for module %s was created",
                lang,
                module_name,
            )
