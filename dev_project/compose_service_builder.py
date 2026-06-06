"""Build ComposeOdooService spec and runtime config for the odoo compose service."""

from __future__ import annotations

from . import constants
from .config import Config
from .config.payload import write_runtime_config
from .inside_docker_app import cli_params
from .start_command import ComposeOdooService, StartCommand


class ComposeServiceBuilder:
    def __init__(self, config: Config) -> None:
        self.config = config
        self.args = self.config.arguments
        self.policy = config.policy

    def build(self) -> ComposeOdooService:
        start_command = self.build_start_command()
        compose_service = start_command.to_compose_service(
            include_runtime_config=self.policy.mount_runtime_config_from_host(),
        )
        self.config.compose_service = compose_service
        self.config.container_run_mode = start_command.run_mode
        if compose_service.include_runtime_config:
            write_runtime_config(self.config)
        return compose_service

    def build_start_command(self) -> StartCommand:
        self.config.generate_odoo_conf_docker_data()
        odoo_bin_path = (
            f"{self.config.docker_odoo_dir}/{self.config.platform_name}-bin"
        )

        if self.args.start_precommit:
            return StartCommand(
                kind="pre_commit",
                pre_commit_project_dir=self.config.docker_odoo_project_dir_path,
            )

        if self.args.export_po_files:
            return StartCommand(
                kind="standard",
                docker_project_dir=self.config.docker_project_dir,
                run_mode=constants.RUN_MODE_BOOTSTRAP_ONLY,
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
                docker_project_dir=self.config.docker_project_dir,
                odoo_bin=odoo_bin,
            )

        odoo_bin = self._build_odoo_bin_argv(odoo_bin_path)
        return StartCommand(
            kind="standard",
            docker_project_dir=self.config.docker_project_dir,
            odoo_bin=odoo_bin,
        )

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
