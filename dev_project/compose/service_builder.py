"""Build ComposeOdooService spec and runtime config for the odoo compose service."""

from __future__ import annotations

from typing import TYPE_CHECKING

from .. import constants
from ..config.transforms import modules_csv_for_odoo_flag
from ..dev_mode import effective_dev_mode
from ..host.cli import params as cli_params
from .start_command import ComposeOdooService, StartCommand
if TYPE_CHECKING:
    from ..host.context import HostProjectContext
    from ..host.ports import BootstrapHandle


def persist_runtime_config(bootstrap: BootstrapHandle) -> None:
    """Write ``.odpm/runtime/config.json`` (patchable seam for unit tests)."""

    bootstrap.write_runtime_config()


class ComposeServiceBuilder:
    def __init__(
        self,
        bootstrap: BootstrapHandle,
        *,
        host_ctx: HostProjectContext | None = None,
    ) -> None:
        self.bootstrap = bootstrap
        if host_ctx is not None:
            self.host_ctx = host_ctx
        else:

            self.host_ctx = bootstrap.host_context()
        self.args = self.host_ctx.arguments
        self.policy = self.host_ctx.policy

    def build(self) -> ComposeOdooService:
        start_command = self.build_start_command()
        compose_service = start_command.to_compose_service(
            include_runtime_config=self.policy.mount_runtime_config_from_host(),
        )
        self.bootstrap.runtime.compose_service = compose_service
        self.bootstrap.runtime.container_run_mode = start_command.run_mode
        if compose_service.include_runtime_config:
            persist_runtime_config(self.bootstrap)
        if self.policy.mount_runtime_secrets_from_host():
            from ..project_env.secrets import materialize_secrets  # noqa: PLC0415  # optional

            compose_service.include_runtime_secrets = materialize_secrets(
                self.host_ctx.project_dir
            )
        return compose_service

    def build_start_command(self) -> StartCommand:
        self.bootstrap.generate_odoo_conf_docker_data()
        layout = self.host_ctx.docker_layout
        odoo_bin_path = (
            f"{layout.docker_odoo_dir}/"
            f"{self.host_ctx.project_settings.platform_name}-bin"
        )

        if self.args.start_precommit:
            return StartCommand(
                kind="pre_commit",
                docker_project_dir=layout.docker_project_dir,
                pre_commit_project_dir=layout.docker_odoo_project_dir_path,
            )

        if self.args.export_po_files:
            return StartCommand(
                kind="standard",
                docker_project_dir=layout.docker_project_dir,
                run_mode=constants.RUN_MODE_BOOTSTRAP_ONLY,
            )

        if self.args.scaffold_module_name is not None:
            odoo_bin = [
                odoo_bin_path,
                "scaffold",
                self.args.scaffold_module_name,
                layout.docker_odoo_project_dir_path,
            ]
            if self.args.scaffold_template_name:
                odoo_bin.extend(["-t", self.args.scaffold_template_name])
            return StartCommand(
                kind="standard",
                docker_project_dir=layout.docker_project_dir,
                odoo_bin=odoo_bin,
            )

        odoo_bin = self._build_odoo_bin_argv(odoo_bin_path)
        return StartCommand(
            kind="standard",
            docker_project_dir=layout.docker_project_dir,
            odoo_bin=odoo_bin,
        )

    def _build_odoo_bin_argv(self, odoo_bin_path: str) -> list[str]:
        layout = self.host_ctx.docker_layout
        argv = [
            odoo_bin_path,
            "-c",
            f"{layout.docker_project_dir}/odoo.conf",
            "--limit-time-real",
            "99999",
        ]

        if self.args.d:
            argv.extend([cli_params.D_PARAM, self.args.d])

        init_modules = modules_csv_for_odoo_flag(
            self.args.i, self.host_ctx.user_settings.init_modules
        )
        if init_modules:
            argv.extend([cli_params.I_PARAM, init_modules])

        update_modules = modules_csv_for_odoo_flag(
            self.args.u, self.host_ctx.user_settings.update_modules
        )
        if update_modules:
            argv.extend([cli_params.U_PARAM, update_modules])

        if self.args.test:
            argv.extend(["--test-enable", "--stop-after-init"])
            if self.args.screencasts:
                argv.extend(
                    [
                        cli_params.SCREENCASTS_PARAM,
                        layout.docker_temp_tests_dir,
                    ]
                )

        if self.args.translate:
            lang_param = "--language"
            if float(self.host_ctx.project_settings.odoo_version) >= 19:
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

        dev_mode = effective_dev_mode(
            self.host_ctx.user_settings.dev_mode,
            apply_dev_mode=self.policy.apply_dev_mode,
        )
        if dev_mode:
            argv.extend(["--dev", str(dev_mode)])

        argv.extend(self._extra_odoo_bin_tokens(argv))
        return argv

    def _extra_odoo_bin_tokens(self, reserved_argv: list[str]) -> list[str]:
        extra = list(self.args.odoo_bin or [])
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
