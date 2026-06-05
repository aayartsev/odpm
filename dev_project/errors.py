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
