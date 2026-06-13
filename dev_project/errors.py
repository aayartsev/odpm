"""Host-side odpm error hierarchy."""


class OdpmError(Exception):
    def __init__(self, message: str, *, exit_code: int = 1) -> None:
        self.exit_code = exit_code
        super().__init__(message)


class PipelineError(OdpmError):
    pass


class ConfigError(OdpmError):
    pass


class SystemCheckError(OdpmError):
    pass


class ProjectDirError(OdpmError):
    pass


class GitError(OdpmError):
    pass


class SubprocessError(OdpmError):
    def __init__(
        self,
        message: str,
        *,
        argv: list[str],
        returncode: int,
        stdout: str = "",
        stderr: str = "",
        exit_code: int = 1,
    ) -> None:
        self.argv = argv
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        super().__init__(message, exit_code=exit_code)
