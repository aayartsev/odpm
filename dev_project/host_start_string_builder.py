import base64
import pathlib
import re

from . import constants
from .host_config import Config
from .inside_docker_app import cli_params
class ArgumentParser:
    def __init__(self, args_list=[]) -> None:
        self.args_list = args_list
        if args_list:
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


class StartStringBuilder:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.args = self.config.arguments
        self.policy = config.policy
        self.config.start_string = self.get_start_string()

    def get_base64_string_config(self) -> str:
        data = self.config.config_to_json()
        config_base64_data = base64.b64encode(data)
        return config_base64_data.decode()

    def build_entrypoint_invocation(self) -> str:
        return f"python3 -m {self.policy.entrypoint_module}"

    def build_debugger_prefix(self) -> str:
        if not self.policy.include_debugpy:
            return ""
        return f"-m debugpy --listen 0.0.0.0:{constants.DEBUGGER_DOCKER_PORT} "

    def build_odoo_bin_command(self) -> str:
        debugger_command_string = self.build_debugger_prefix()
        return (
            f"python3 -u {debugger_command_string}"
            f"{self.config.docker_odoo_dir}/{self.config.platform_name}-bin"
        )

    def create_string_with_params_for_odoo_bin(self) -> str:
        final_string = ""
        parser = ArgumentParser()
        odoo_bin_params_dict = parser.get_dict_of_args(
            vars(self.args).get("odoo_bin", []), False
        )
        start_python_command_dict = parser.get_dict_of_args(
            self.start_python_command.split(" "), False
        )
        for key_to_exclude in start_python_command_dict:
            odoo_bin_params_dict.pop(key_to_exclude, None)
        args_dict_to_string = ArgsDictToString()
        if odoo_bin_params_dict:
            final_string = args_dict_to_string.get_string_from_dict(
                odoo_bin_params_dict
            )
        return final_string

    def get_start_string(self) -> str:
        self.config.generate_odoo_conf_docker_data()
        start_odoo_bin_command = self.build_odoo_bin_command()
        self.start_python_command = (
            f"{start_odoo_bin_command} -c {self.config.docker_project_dir}/odoo.conf "
            f"--limit-time-real 99999"
        )
        db_name = self.args.d
        translate_lang = self.args.translate
        install_pip = self.args.pip_install
        start_pre_commit = self.args.start_precommit
        export_po_files_lang = self.args.export_po_files
        dev_mode = self.config.dev_mode or False

        if install_pip:
            pip_install_command = f"""cd {self.config.docker_project_dir} && python3 -m venv {self.config.docker_venv_dir} && . {pathlib.PurePosixPath(self.config.docker_venv_dir, "bin", "activate")} && wget -O odoo_requirements.txt https://raw.githubusercontent.com/odoo/odoo/{self.config.odoo_version}/requirements.txt && python3 -m pip install -r odoo_requirements.txt && python3 -m pip install {" ".join([req for req in self.config.requirements_txt])}"""
            start_string = f"""bash -c '{pip_install_command}'"""
            return start_string

        if start_pre_commit:
            start_string = f"""/bin/bash -c 'cd {self.config.docker_odoo_project_dir_path} && ls && git config --global --add safe.directory {self.config.docker_odoo_project_dir_path} && pre-commit run --all-files'"""
            return start_string

        if db_name:
            self.start_python_command += f" {cli_params.D_PARAM} {db_name}"

        if self.args.i and self.config.init_modules:
            self.start_python_command += (
                f""" {cli_params.I_PARAM} {self.config.init_modules}"""
            )

        if self.args.u and self.config.update_modules:
            self.start_python_command += (
                f""" {cli_params.U_PARAM} {self.config.update_modules}"""
            )

        if self.args.test:
            self.start_python_command += " --test-enable --stop-after-init"
            if self.args.screencasts:
                self.start_python_command += f""" {cli_params.SCREENCASTS_PARAM} {self.config.docker_temp_tests_dir}"""

        if translate_lang:
            lang_param = "--language"
            if float(self.config.odoo_version) >= 19:
                lang_param = "--load-language"
            self.start_python_command += f" {lang_param} {translate_lang} --load-language {translate_lang} --i18n-overwrite"

        if export_po_files_lang:
            self.start_python_command = "exit 0"

        if dev_mode:
            self.start_python_command += f" --dev {dev_mode}"

        if cli_params.SCAFFOLD_SUBPARSER_MODULE_NAME_PARAM in self.args:
            self.start_python_command = f"""{start_odoo_bin_command} """
            self.start_python_command += f"""scaffold {self.args.scaffold_module_name} {self.config.docker_odoo_project_dir_path}"""
            if self.args.scaffold_template_name:
                self.start_python_command += (
                    f""" -t {self.args.scaffold_template_name}"""
                )

        odoo_bin_additional_params = self.create_string_with_params_for_odoo_bin()
        if odoo_bin_additional_params:
            self.start_python_command += f""" {odoo_bin_additional_params}"""

        entrypoint_invocation = self.build_entrypoint_invocation()
        start_main = " && ".join(
            [
                f"""cd {self.config.docker_project_dir}""",
                f"""{entrypoint_invocation} {cli_params.CONFIG_BASE64_DATA} {self.get_base64_string_config()}""",
                f""". {pathlib.PurePosixPath(self.config.docker_venv_dir, "bin", "activate")}""",
                f"""{self.start_python_command}""",
            ]
        )

        start_string = f"""bash -c '{start_main}'"""

        return start_string
