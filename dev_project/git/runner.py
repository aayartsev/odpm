"""Low-level git subprocess runner with optional SSH key configuration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..logging import get_module_logger
from ..subprocess_runner import CommandResult, run_checked

if TYPE_CHECKING:
    from .link import HandleOdooProjectLink

_logger = get_module_logger(__name__)


class GitRunner:
    def __init__(self, link: HandleOdooProjectLink) -> None:
        self.link = link

    def build_git_cmd(self, args: list[str]) -> list[str]:
        if self.link.path_to_ssh_key:
            return [
                "git",
                "-c",
                f"core.sshCommand=ssh -i {self.link.path_to_ssh_key}",
                *args,
            ]
        return ["git", *args]

    def run_git(
        self,
        args: list[str],
        *,
        cwd: str | None = None,
        capture: bool = True,
    ) -> CommandResult:
        cmd = self.build_git_cmd(args)
        workdir = self.link.project_path if cwd is None else cwd
        if not capture:
            _logger.info(
                f"""running command: → git {" ".join(args)} for {self.link.project_string}"""
            )
        return run_checked(cmd, cwd=workdir, capture=capture)
