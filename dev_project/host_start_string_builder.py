"""Deprecated re-export. Prefer ``dev_project.compose_service_builder``."""

from __future__ import annotations

import re
import warnings

warnings.warn(
    "dev_project.host_start_string_builder is deprecated; "
    "import ComposeServiceBuilder from dev_project.compose_service_builder",
    DeprecationWarning,
    stacklevel=1,
)

from .compose_service_builder import ComposeServiceBuilder as StartStringBuilder

__all__ = ["StartStringBuilder", "ArgumentParser", "ArgsDictToString"]


class ArgumentParser:
    """Deprecated: prefer ``Namespace.odoo_bin`` list args in ``ComposeServiceBuilder``."""

    def __init__(self, args_list=None) -> None:
        warnings.warn(
            "ArgumentParser is deprecated; pass odoo args via Namespace.odoo_bin",
            DeprecationWarning,
            stacklevel=2,
        )
        self.args_list = args_list or []
        if self.args_list:
            self.args_dict = self.get_dict_of_args(self.args_list)

    def get_dict_of_args(self, args_list: list, as_argparse=True) -> dict:
        args_dict = {}
        if not args_list:
            return args_dict
        all_flags_args_keys = re.findall(r"-[a-z]\s|-[a-z]$", " ".join(args_list))
        all_flags_args_keys = [arg.strip() for arg in all_flags_args_keys]
        all_key_args_keys = re.findall(r"--[a-z-_0-9]*", " ".join(args_list))
        all_key_args_keys = [arg.strip() for arg in all_key_args_keys]
        all_args_keys = all_flags_args_keys + all_key_args_keys
        current_index = 0
        while current_index < len(args_list):
            item = args_list[current_index]
            key_item = item
            if as_argparse:
                key_item = item.strip("-").replace("-", "_")
            if (
                current_index < len(args_list) - 1
                and item in all_args_keys
                and args_list[args_list.index(item) + 1] not in all_args_keys
            ):
                args_dict[key_item] = args_list[args_list.index(item) + 1]
                current_index += 2
            else:
                args_dict[key_item] = True
                current_index += 1
        return args_dict


class ArgsDictToString:
    def get_string_from_dict(self, dict_to_string: dict) -> str:
        string_with_params = ""
        for key, value in dict_to_string.items():
            if isinstance(value, bool):
                string_with_params = string_with_params + f" {key}"
            else:
                string_with_params = string_with_params + f" {key} {value}"
        return string_with_params.strip()
