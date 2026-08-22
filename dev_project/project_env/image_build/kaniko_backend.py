"""Kaniko executor backend for CI image builds."""

from __future__ import annotations

import os
import shlex
import shutil
import subprocess
from pathlib import Path

from ... import constants
from ...errors import PipelineError
from ...logging import get_module_logger
from ...subprocess_runner import run_logged
from ...translations import _
from .resolve import _truthy_env
from .spec import ImageBuildSpec

_logger = get_module_logger(__name__)


def _split_env_argv(raw: str | None) -> list[str]:
    if raw is None:
        return []
    text = raw.strip()
    if not text:
        return []
    return shlex.split(text)


class KanikoImageBuildBackend:
    def __init__(
        self,
        *,
        environ: dict[str, str] | None = None,
        home_dir: str | None = None,
    ) -> None:
        self._environ = environ if environ is not None else os.environ
        self._home_dir = home_dir if home_dir is not None else str(Path.home())

    def _executor_mode(self) -> str:
        raw = (
            self._environ.get(constants.ODPM_KANIKO_EXECUTOR_MODE_ENV, "")
            or constants.KANIKO_EXECUTOR_MODE_DOCKER_RUN
        ).strip().lower()
        if raw not in constants.KANIKO_EXECUTOR_MODES:
            message = _(
                "Unknown Kaniko executor mode {MODE!r}; expected one of: {ALLOWED}"
            ).format(
                MODE=raw,
                ALLOWED=", ".join(constants.KANIKO_EXECUTOR_MODES),
            )
            raise PipelineError(message)
        return raw

    def _executor_image(self) -> str:
        return (
            self._environ.get(constants.ODPM_KANIKO_EXECUTOR_IMAGE_ENV, "")
            or constants.DEFAULT_KANIKO_EXECUTOR_IMAGE
        ).strip()

    def _executor_bin(self) -> str:
        return (
            self._environ.get(constants.ODPM_KANIKO_EXECUTOR_BIN_ENV, "")
            or constants.DEFAULT_KANIKO_EXECUTOR_BIN
        ).strip()

    def _executor_wrapper_argv(self) -> list[str]:
        return _split_env_argv(
            self._environ.get(constants.ODPM_KANIKO_EXECUTOR_WRAPPER_ENV)
        )

    def _executor_extra_flags(self) -> list[str]:
        return _split_env_argv(
            self._environ.get(constants.ODPM_KANIKO_EXECUTOR_EXTRA_FLAGS_ENV)
        )

    def _executor_sudo_enabled(self) -> bool:
        return _truthy_env(
            self._environ.get(constants.ODPM_KANIKO_EXECUTOR_SUDO_ENV)
        )

    def _docker_config_path(self) -> str:
        return os.path.join(self._home_dir, ".docker", "config.json")

    @staticmethod
    def _running_as_non_root() -> bool:
        if not hasattr(os, "geteuid"):
            return False
        return os.geteuid() != 0

    def _validate_wrapper_executable(self, wrapper_argv: list[str]) -> None:
        if not wrapper_argv:
            return
        head = wrapper_argv[0]
        if not (head.startswith("/") or head.startswith(".")):
            return
        if not os.path.isfile(head):
            message = _(
                "Kaniko executor wrapper {PATH} is not a file; "
                "check {ENV}."
            ).format(
                PATH=head,
                ENV=constants.ODPM_KANIKO_EXECUTOR_WRAPPER_ENV,
            )
            raise PipelineError(message)
        if not os.access(head, os.X_OK):
            message = _(
                "Kaniko executor wrapper {PATH} is not executable; "
                "check {ENV}."
            ).format(
                PATH=head,
                ENV=constants.ODPM_KANIKO_EXECUTOR_WRAPPER_ENV,
            )
            raise PipelineError(message)

    def _validate_passwordless_sudo(self) -> None:
        sudo = shutil.which("sudo")
        if sudo is None:
            message = _(
                "{ENV}=1 requires sudo on PATH for Kaniko direct mode."
            ).format(ENV=constants.ODPM_KANIKO_EXECUTOR_SUDO_ENV)
            raise PipelineError(message)
        result = subprocess.run(
            [sudo, "-n", "true"],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            message = _(
                "Kaniko direct mode with {ENV}=1 requires passwordless sudo "
                "(sudo -n true failed). Configure sudoers for the executor "
                "binary or set {WRAPPER_ENV} instead."
            ).format(
                ENV=constants.ODPM_KANIKO_EXECUTOR_SUDO_ENV,
                WRAPPER_ENV=constants.ODPM_KANIKO_EXECUTOR_WRAPPER_ENV,
            )
            raise PipelineError(message)

    def validate_direct_launch(self) -> None:
        """Fail fast when ``direct`` cannot run a privileged executor."""
        if self._executor_mode() != constants.KANIKO_EXECUTOR_MODE_DIRECT:
            return
        wrapper = self._executor_wrapper_argv()
        self._validate_wrapper_executable(wrapper)
        if not self._running_as_non_root():
            return
        if wrapper:
            return
        if self._executor_sudo_enabled():
            self._validate_passwordless_sudo()
            return
        message = _(
            "Kaniko direct mode requires a privileged executor launch while "
            "odpm runs as a non-root user. Set {WRAPPER_ENV} to a script that "
            "runs {BIN_ENV} as root (recommended), or set {SUDO_ENV}=1 with "
            "passwordless sudo for the executor binary. odpm itself must not "
            "run as root."
        ).format(
            WRAPPER_ENV=constants.ODPM_KANIKO_EXECUTOR_WRAPPER_ENV,
            BIN_ENV=constants.ODPM_KANIKO_EXECUTOR_BIN_ENV,
            SUDO_ENV=constants.ODPM_KANIKO_EXECUTOR_SUDO_ENV,
        )
        raise PipelineError(message)

    def kaniko_flags(self, spec: ImageBuildSpec, *, workspace: str) -> list[str]:
        dockerfile_name = os.path.basename(spec.dockerfile)
        flags = [
            f"--dockerfile={workspace}/{dockerfile_name}",
            f"--context=dir://{workspace}",
            f"--custom-platform={spec.platform}",
        ]
        if spec.push:
            flags.append(f"--destination={spec.tag}")
        else:
            flags.extend(
                [
                    "--no-push",
                    f"--tar-path={workspace}/{constants.CI_IMAGE_TAR_NAME}",
                ]
            )
        return flags

    def _direct_executor_argv(self, spec: ImageBuildSpec) -> list[str]:
        wrapper = self._executor_wrapper_argv()
        extra = self._executor_extra_flags()
        executor_bin = self._executor_bin()
        flags = self.kaniko_flags(spec, workspace=spec.context_dir)
        argv: list[str] = list(wrapper)
        if (
            not wrapper
            and self._executor_sudo_enabled()
            and self._running_as_non_root()
        ):
            argv.extend(["sudo", "-n"])
        argv.append(executor_bin)
        argv.extend(extra)
        argv.extend(flags)
        return argv

    def build_argv(self, spec: ImageBuildSpec) -> list[str]:
        mode = self._executor_mode()
        if mode == constants.KANIKO_EXECUTOR_MODE_DIRECT:
            return self._direct_executor_argv(spec)

        if spec.push and not os.path.isfile(self._docker_config_path()):
            message = _(
                "Kaniko --image-push in docker-run mode requires {PATH} "
                "(docker login credentials). Create it, or use ODPM_KANIKO_EXECUTOR_MODE=direct "
                "with registry credentials available to the executor."
            ).format(PATH=self._docker_config_path())
            raise PipelineError(message)

        argv = [
            "docker",
            "run",
            "--rm",
            "-v",
            f"{spec.context_dir}:/workspace",
        ]
        docker_config = self._docker_config_path()
        if spec.push:
            argv.extend(
                [
                    "-v",
                    f"{docker_config}:/kaniko/.docker/config.json:ro",
                ]
            )
        argv.append(self._executor_image())
        argv.extend(self.kaniko_flags(spec, workspace="/workspace"))
        return argv

    def build(self, spec: ImageBuildSpec) -> None:
        self.validate_direct_launch()
        argv = self.build_argv(spec)
        _logger.info("kaniko backend: %s", " ".join(argv))
        returncode = run_logged(argv, cwd=spec.project_dir)
        if returncode != 0:
            message = _("kaniko build failed with exit code {EXIT_CODE}").format(
                EXIT_CODE=returncode
            )
            _logger.error(message)
            raise PipelineError(message, exit_code=returncode)
