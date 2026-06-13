"""Container-side error hierarchy (separate from host ``dev_project.errors``)."""


class ContainerError(Exception):
    def __init__(self, message: str, *, exit_code: int = 1) -> None:
        self.exit_code = exit_code
        super().__init__(message)


class VenvError(ContainerError):
    pass


class ConfigValidationError(ContainerError):
    pass


class PostgresError(ContainerError):
    pass


class OdooStartupError(ContainerError):
    pass


class NonExistentParameter(ContainerError):
    """Legacy name kept for backward compatibility."""

    def __init__(self, message: str) -> None:
        super().__init__(message, exit_code=1)
