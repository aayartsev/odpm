import base64
import pathlib
import re
import warnings

from . import constants
from .config import Config
from .inside_docker_app import cli_params
from .start_command import StartCommand


class ArgumentParser:
    """Deprecated: prefer ``Namespace.odoo_bin`` list args in ``StartStringBuilder``."""

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


class StartStringBuilder:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.args = self.config.arguments
        self.policy = config.policy

    def build(self) -> str:
        start_command = self.build_start_command()
        start_string = start_command.to_compose_shell()
        self.config.start_string = start_string
        return start_string

    def build_start_command(self) -> StartCommand:
        self.config.generate_odoo_conf_docker_data()
        odoo_bin_path = (
            f"{self.config.docker_odoo_dir}/{self.config.platform_name}-bin"
        )

        if self.args.pip_install:
            pip_install_command = (
                f"cd {self.config.docker_project_dir} && python3 -m venv "
                f"{self.config.docker_venv_dir} && . "
                f"{pathlib.PurePosixPath(self.config.docker_venv_dir, 'bin', 'activate')} "
                f"&& wget -O odoo_requirements.txt "
                f"https://raw.githubusercontent.com/odoo/odoo/{self.config.odoo_version}/requirements.txt "
                f"&& python3 -m pip install -r odoo_requirements.txt && python3 -m pip install "
                f"{' '.join([req for req in self.config.requirements_txt])}"
            )
            return StartCommand(
                kind="pip_install",
                pip_install_script=pip_install_command,
            )

        if self.args.start_precommit:
            pre_commit_script = (
                f"cd {self.config.docker_odoo_project_dir_path} && ls && "
                f"git config --global --add safe.directory "
                f"{self.config.docker_odoo_project_dir_path} && pre-commit run --all-files"
            )
            return StartCommand(
                kind="pre_commit",
                pre_commit_script=pre_commit_script,
            )

        if self.args.export_po_files:
            return StartCommand(
                kind="standard",
                entrypoint=self._entrypoint_argv(),
                config_b64=self.get_base64_string_config(),
                docker_project_dir=self.config.docker_project_dir,
                docker_venv_dir=self.config.docker_venv_dir,
                debugpy=self.policy.include_debugpy,
                odoo_shell_override="exit 0",
            )

        if cli_params.SCAFFOLD_SUBPARSER_MODULE_NAME_PARAM in self.args:
            odoo_bin = [
                odoo_bin_path,
                "scaffold",
                self.args.scaffold_module_name,
                self.config.docker_odoo_project_dir_path,
            ]
            if self.args.scaffold_template_name:
                odoo_bin.extend(["-t", self.args.scaffold_template_name])
            return StartCommand(
                kind="standard",
                entrypoint=self._entrypoint_argv(),
                config_b64=self.get_base64_string_config(),
                docker_project_dir=self.config.docker_project_dir,
                docker_venv_dir=self.config.docker_venv_dir,
                debugpy=self.policy.include_debugpy,
                odoo_bin=odoo_bin,
            )

        odoo_bin = self._build_odoo_bin_argv(odoo_bin_path)
        return StartCommand(
            kind="standard",
            entrypoint=self._entrypoint_argv(),
            config_b64=self.get_base64_string_config(),
            docker_project_dir=self.config.docker_project_dir,
            docker_venv_dir=self.config.docker_venv_dir,
            debugpy=self.policy.include_debugpy,
            odoo_bin=odoo_bin,
        )

    def _entrypoint_argv(self) -> list[str]:
        return ["python3", "-m", self.policy.entrypoint_module]

    def get_base64_string_config(self) -> str:
        data = self.config.config_to_json()
        config_base64_data = base64.b64encode(data)
        return config_base64_data.decode()

    def _build_odoo_bin_argv(self, odoo_bin_path: str) -> list[str]:
        argv = [
            odoo_bin_path,
            "-c",
            f"{self.config.docker_project_dir}/odoo.conf",
            "--limit-time-real",
            "99999",
        ]

        if self.args.d:
            argv.extend([cli_params.D_PARAM, self.args.d])

        if self.args.i and self.config.init_modules:
            argv.extend([cli_params.I_PARAM, self.config.init_modules])

        if self.args.u and self.config.update_modules:
            argv.extend([cli_params.U_PARAM, self.config.update_modules])

        if self.args.test:
            argv.extend(["--test-enable", "--stop-after-init"])
            if self.args.screencasts:
                argv.extend(
                    [cli_params.SCREENCASTS_PARAM, self.config.docker_temp_tests_dir]
                )

        if self.args.translate:
            lang_param = "--language"
            if float(self.config.odoo_version) >= 19:
                lang_param = "--load-language"
            argv.extend(
                [
                    lang_param,
                    self.args.translate,
                    "--load-language",
                    self.args.translate,
                    "--i18n-overwrite",
                ]
            )

        dev_mode = self.config.dev_mode or False
        if dev_mode:
            argv.extend(["--dev", str(dev_mode)])

        argv.extend(self._extra_odoo_bin_tokens(argv))
        return argv

    def _extra_odoo_bin_tokens(self, reserved_argv: list[str]) -> list[str]:
        extra = list(getattr(self.args, "odoo_bin", None) or [])
        if not extra:
            return []

        reserved = set(reserved_argv)
        filtered: list[str] = []
        index = 0
        while index < len(extra):
            token = extra[index]
            if token in reserved:
                index += 2 if index + 1 < len(extra) else 1
                continue
            filtered.append(token)
            index += 1
        return filtered

    def get_start_string(self) -> str:
        return self.build()
