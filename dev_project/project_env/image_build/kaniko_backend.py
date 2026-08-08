"""Kaniko executor backend for CI image builds."""

from __future__ import annotations

import os
from pathlib import Path

from ... import constants
from ...errors import PipelineError
from ...logging import get_module_logger
from ...subprocess_runner import run_logged
from ...translations import _
from .spec import ImageBuildSpec

_logger = get_module_logger(__name__)


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

    def _docker_config_path(self) -> str:
        return os.path.join(self._home_dir, ".docker", "config.json")

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

    def build_argv(self, spec: ImageBuildSpec) -> list[str]:
        mode = self._executor_mode()
        if mode == constants.KANIKO_EXECUTOR_MODE_DIRECT:
            return [self._executor_bin(), *self.kaniko_flags(spec, workspace=spec.context_dir)]

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
        argv = self.build_argv(spec)
        _logger.info("kaniko backend: %s", " ".join(argv))
        returncode = run_logged(argv, cwd=spec.project_dir)
        if returncode != 0:
            message = _("kaniko build failed with exit code {EXIT_CODE}").format(
                EXIT_CODE=returncode
            )
            _logger.error(message)
            raise PipelineError(message, exit_code=returncode)
