"""Download Odoo platform sources (nightly zip for server scenario)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import TYPE_CHECKING

from ... import constants
from ...inside_docker_app.utils import (
    delete_files_in_directory,
    download_file,
    un_zip_file_to_directory,
)

if TYPE_CHECKING:
    from ..environment import CreateProjectEnvironment


class PlatformSourcesService:
    def __init__(self, env: CreateProjectEnvironment) -> None:
        self.env = env

    @property
    def config(self):
        return self.env.config

    def download_odoo_nightly_build(self) -> None:
        self.env._require_system_checker().check_free_space_for_odoo_developing(
            free_space_size=2.0
        )
        parent_dir = os.path.dirname(self.config.odoo_src_dir)
        delete_files_in_directory(self.config.odoo_src_dir)
        odoo_version = self.config.odoo_version
        odoo_build_date = (
            self.config.odoo_build_date or constants.ODOO_DEFAULT_BUILD_DATE
        )
        link_to_download = (
            f"https://nightly.odoo.com/{odoo_version}/nightly/src/"
            f"odoo_{odoo_version}.{odoo_build_date}.zip"
        )
        filepath_to_save = os.path.join(Path.home(), "odoo.zip.download")
        download_file(
            link_to_download=link_to_download,
            filepath_to_save=filepath_to_save,
        )
        un_zip_file_to_directory(
            parent_dir,
            filepath_to_save,
            rename_first_part_of_path="odoo",
        )
        os.replace(
            os.path.join(self.config.odoo_src_dir, "setup", "odoo"),
            os.path.join(self.config.odoo_src_dir, "odoo-bin"),
        )
        if os.path.exists(filepath_to_save):
            os.remove(filepath_to_save)
