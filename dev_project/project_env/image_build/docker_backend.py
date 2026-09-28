"""Docker CLI backend for CI image builds."""

from __future__ import annotations

from ...errors import PipelineError
from ...logging import get_module_logger
from ...subprocess_runner import run_logged
from ...translations import _
from .spec import ImageBuildSpec

_logger = get_module_logger(__name__)


class DockerImageBuildBackend:
    def build_argv(self, spec: ImageBuildSpec) -> list[str]:
        return [
            "docker",
            "build",
            "-f",
            spec.dockerfile,
            "-t",
            spec.tag,
            f"--platform={spec.platform}",
            spec.context_dir,
        ]

    def push_argv(self, spec: ImageBuildSpec) -> list[str]:
        return ["docker", "push", spec.tag]

    def build(self, spec: ImageBuildSpec) -> None:
        argv = self.build_argv(spec)
        _logger.info("docker backend: %s", " ".join(argv))
        returncode = run_logged(argv, cwd=spec.project_dir)
        if returncode != 0:
            message = _("docker build failed with exit code {EXIT_CODE}").format(
                EXIT_CODE=returncode
            )
            _logger.error(message)
            raise PipelineError(message, exit_code=returncode)
        if not spec.push:
            return
        push_argv = self.push_argv(spec)
        _logger.info("docker backend: %s", " ".join(push_argv))
        push_code = run_logged(push_argv, cwd=spec.project_dir)
        if push_code != 0:
            message = _("docker push failed with exit code {EXIT_CODE}").format(
                EXIT_CODE=push_code
            )
            _logger.error(message)
            raise PipelineError(message, exit_code=push_code)
