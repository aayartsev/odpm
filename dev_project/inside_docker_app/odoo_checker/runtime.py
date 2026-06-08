"""Load Odoo platform module and environment context for container bootstrap."""

from __future__ import annotations

import importlib
import os
import sys
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Any, Callable, ContextManager

USED_ODOO_SUBMODULES = ("tools", "api", "service")


@dataclass(frozen=True)
class LoadedOdooRuntime:
    odoo: Any
    odoo_config_object: Any
    int_odoo_version: int
    odoo_version_info: tuple[int, ...]
    environment_manage: Callable[[], ContextManager[None]]


def load_odoo_runtime(*, platform_name: str, odoo_dir: str) -> LoadedOdooRuntime:
    odoo_src_dir = os.path.abspath(odoo_dir)
    if odoo_src_dir not in sys.path:
        sys.path.insert(0, odoo_src_dir)

    odoo = importlib.import_module(platform_name)
    for submodule in USED_ODOO_SUBMODULES:
        if not getattr(odoo, submodule, None):
            setattr(
                odoo,
                submodule,
                importlib.import_module(f"{platform_name}.{submodule}"),
            )

    odoo_config_object = odoo.tools.config
    Environment = odoo.api.Environment
    odoo_version_info = odoo.release.version_info
    if odoo_version_info < (15, 0):
        environment_manage = Environment.manage
    else:

        @contextmanager
        def environment_manage():
            yield

    return LoadedOdooRuntime(
        odoo=odoo,
        odoo_config_object=odoo_config_object,
        int_odoo_version=odoo_version_info[0],
        odoo_version_info=odoo_version_info,
        environment_manage=environment_manage,
    )


def apply_odoo_config(
    runtime: LoadedOdooRuntime,
    *,
    odoo_config_data: dict,
    docker_path_odoo_conf: str,
) -> None:
    from ..utils import write_odoo_config_data_to_file

    write_odoo_config_data_to_file(odoo_config_data, docker_path_odoo_conf)
    runtime.odoo.tools.config.parse_config(["-c", docker_path_odoo_conf])
    runtime.odoo_config_object["list_db"] = True
